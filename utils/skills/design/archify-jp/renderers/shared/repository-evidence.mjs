import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { throwDiagnosticError } from './diagnostics.mjs';

const FULL_SHA_RE = /^[a-f0-9]{40}$/i;
const CONTROL_CHARACTER_RE = /[\u0000-\u001f\u007f]/;

function evidenceFailure(code, message, { subject = {}, evidence = {}, supportedFixes = [] } = {}) {
  throwDiagnosticError(message, [{
    code,
    severity: 'error',
    message,
    subject: { surface: 'repository-evidence', ...subject },
    evidence,
    supportedFixes,
  }]);
}

function runGit(repoRoot, args) {
  const result = spawnSync('git', ['-C', repoRoot, ...args], {
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) evidenceFailure('repository-evidence/git-unavailable', `Gitを実行できませんでした: ${result.error.message}`, {
    evidence: { reason: result.error.message },
    supportedFixes: ['Gitをインストールし、PATHから利用できることを確認する'],
  });
  return result;
}

function gitValue(repoRoot, args, failure) {
  const result = runGit(repoRoot, args);
  if (result.status !== 0) evidenceFailure('repository-evidence/git-command', failure, {
    evidence: { gitArgs: args, exitCode: result.status },
    supportedFixes: ['意図したローカルGitリポジトリを使用し、そのoriginとrevisionを確認する'],
  });
  return result.stdout.trim();
}

function githubSlug(value) {
  const raw = String(value || '').trim();
  const match = raw.match(/^(?:https:\/\/github\.com\/|git@github\.com:|ssh:\/\/git@github\.com\/)([^/\s]+)\/([^/\s]+?)(?:\.git)?\/?$/i);
  return match ? `${match[1]}/${match[2]}`.toLowerCase() : null;
}

function verifiedSourcePath(value, where) {
  const sourcePath = String(value || '');
  if (!sourcePath || sourcePath.startsWith('/') || sourcePath.includes('\\') || CONTROL_CHARACTER_RE.test(sourcePath)) {
    evidenceFailure('repository-evidence/path-invalid', `${where}はリポジトリ相対のPOSIXパスでなければなりません。`, {
      subject: { path: where },
      evidence: { authoredPath: sourcePath },
      supportedFixes: ['スラッシュ区切りのリポジトリ相対パスを使用する'],
    });
  }
  const segments = sourcePath.split('/');
  if (segments.some((segment) => !segment || segment === '.' || segment === '..') || segments[0] === '.git') {
    evidenceFailure('repository-evidence/path-escape', `${where}はリポジトリ内に留め、.gitを参照してはいけません。`, {
      subject: { path: where },
      evidence: { authoredPath: sourcePath },
      supportedFixes: ['空、ドット、親、または.gitのパス区間を削除する'],
    });
  }
  return segments.join('/');
}

function sourceHref(repositoryUrl, revision, source) {
  const encodedPath = source.path.split('/').map(encodeURIComponent).join('/');
  const lineFragment = source.line
    ? `#L${source.line}${source.endLine && source.endLine !== source.line ? `-L${source.endLine}` : ''}`
    : '';
  return `${repositoryUrl}/blob/${revision}/${encodedPath}${lineFragment}`;
}

function sourceLineCount(content) {
  if (!content.length) return 0;
  const lines = content.split(/\r\n|\n|\r/);
  return lines.length - (/(?:\r\n|\n|\r)$/.test(content) ? 1 : 0);
}

export function hasRepositoryEvidence(diagramType, diagram) {
  if (diagramType !== 'architecture') return false;
  const components = Array.isArray(diagram?.components) ? diagram.components : [];
  return Boolean(diagram?.meta?.repository) || components.some((component) => Array.isArray(component?.sources) && component.sources.length);
}

export function verifyRepositoryEvidence(diagramType, diagram, repoRootInput) {
  if (!hasRepositoryEvidence(diagramType, diagram)) return null;
  if (diagramType !== 'architecture') evidenceFailure('repository-evidence/type-unsupported', 'リポジトリ証拠は現在architecture図だけに対応しています。', {
    subject: { diagramType },
    supportedFixes: ['architectureモードを使用するか、リポジトリ証拠を削除する'],
  });

  const repository = diagram.meta?.repository;
  if (!repository) evidenceFailure('repository-evidence/repository-required', 'リポジトリ証拠には/meta/repositoryが必要です。', {
    subject: { path: '/meta/repository' },
    supportedFixes: ['固定済みの公開リポジトリメタデータを追加するか、コンポーネントのsourcesを削除する'],
  });
  if (!FULL_SHA_RE.test(repository.revision || '')) {
    evidenceFailure('repository-evidence/revision-invalid', '/meta/repository/revisionは完全な40文字のcommit SHAでなければなりません。', {
      subject: { path: '/meta/repository/revision' },
      evidence: { revision: repository.revision },
      supportedFixes: ['完全な40文字のcommit SHAを1つ固定する'],
    });
  }
  const authoredSlug = githubSlug(repository.url);
  if (!authoredSlug || !String(repository.url).startsWith('https://github.com/')) {
    evidenceFailure('repository-evidence/url-invalid', '/meta/repository/urlは公開https://github.comのowner/repository URLでなければなりません。', {
      subject: { path: '/meta/repository/url' },
      evidence: { repositoryUrl: repository.url },
      supportedFixes: ['正規の公開GitHub HTTPSリポジトリURLを使用する'],
    });
  }
  if (!repoRootInput) {
    evidenceFailure('repository-evidence/root-required', 'この図にはソース証拠が宣言されています。レンダリング前にArchifyが検証できるよう、--repo-root <repository>を渡してください。', {
      subject: { path: '/meta/repository' },
      supportedFixes: ['一致するローカルGitチェックアウトを--repo-rootに渡す'],
    });
  }

  const requestedRoot = path.resolve(repoRootInput);
  let realRoot;
  try {
    realRoot = fs.realpathSync(requestedRoot);
  } catch (error) {
    evidenceFailure('repository-evidence/root-unreadable', `証拠リポジトリのルート「${requestedRoot}」を解決できませんでした: ${error.message}`, {
      subject: { repoRoot: requestedRoot },
      evidence: { reason: error.message },
      supportedFixes: ['読み取り可能なローカルリポジトリディレクトリを1つ渡す'],
    });
  }
  const gitRoot = gitValue(realRoot, ['rev-parse', '--show-toplevel'], `証拠ルート「${realRoot}」はGitリポジトリではありません。`);
  if (fs.realpathSync(gitRoot) !== realRoot) {
    evidenceFailure('repository-evidence/root-not-top-level', `証拠ルートはGitの最上位ディレクトリでなければなりません: ${gitRoot}`, {
      subject: { repoRoot: realRoot },
      evidence: { gitTopLevel: gitRoot },
      supportedFixes: [`--repo-root ${gitRoot}を渡す`],
    });
  }
  const origin = gitValue(realRoot, ['remote', 'get-url', 'origin'], '証拠リポジトリにはoriginリモートが必要です。');
  if (githubSlug(origin) !== authoredSlug) {
    evidenceFailure('repository-evidence/origin-mismatch', `証拠リポジトリのorigin ${JSON.stringify(origin)}が${JSON.stringify(repository.url)}と一致しません。`, {
      subject: { repoRoot: realRoot },
      evidence: { localOrigin: origin, authoredRepository: repository.url },
      supportedFixes: ['一致するローカルチェックアウトを使用するか、作成済みrepository URLを修正する'],
    });
  }

  const revision = repository.revision.toLowerCase();
  const commit = runGit(realRoot, ['cat-file', '-e', `${revision}^{commit}`]);
  if (commit.status !== 0) {
    evidenceFailure('repository-evidence/revision-unavailable', `証拠リビジョン${revision}はローカルリポジトリで利用できません。`, {
      subject: { repoRoot: realRoot },
      evidence: { revision },
      supportedFixes: ['固定済みcommitを取得するか、利用可能な完全なcommit SHAを固定する'],
    });
  }

  const nodes = Object.create(null);
  let referenceCount = 0;
  const components = Array.isArray(diagram.components) ? diagram.components : [];
  for (const [componentIndex, component] of components.entries()) {
    if (!Array.isArray(component.sources) || component.sources.length === 0) continue;
    const verified = [];
    for (const [sourceIndex, authored] of component.sources.entries()) {
      const where = `/components/${componentIndex}/sources/${sourceIndex}/path`;
      const source = {
        path: verifiedSourcePath(authored.path, where),
        ...(authored.line ? { line: authored.line } : {}),
        ...(authored.end_line ? { endLine: authored.end_line } : {}),
        ...(authored.label ? { label: authored.label } : {}),
      };
      if (source.endLine && !source.line) {
        evidenceFailure('repository-evidence/line-required', `/components/${componentIndex}/sources/${sourceIndex}/end_lineにはlineが必要です。`, {
          subject: { path: `/components/${componentIndex}/sources/${sourceIndex}/end_line`, componentId: component.id },
          supportedFixes: ['lineを追加するかend_lineを削除する'],
        });
      }
      if (source.endLine && source.endLine < source.line) {
        evidenceFailure('repository-evidence/line-range-invalid', `/components/${componentIndex}/sources/${sourceIndex}/end_lineはline以上でなければなりません。`, {
          subject: { path: `/components/${componentIndex}/sources/${sourceIndex}`, componentId: component.id },
          evidence: { line: source.line, endLine: source.endLine },
          supportedFixes: ['line以上のend_lineを使用する'],
        });
      }
      const object = `${revision}:${source.path}`;
      const type = runGit(realRoot, ['cat-file', '-t', object]);
      if (type.status !== 0 || type.stdout.trim() !== 'blob') {
        evidenceFailure('repository-evidence/file-missing', `${where}はリビジョン${revision}にあるファイルを指していません。`, {
          subject: { path: where, componentId: component.id },
          evidence: { sourcePath: source.path, revision },
          supportedFixes: ['固定済みリビジョンに存在するファイルパスを使用する'],
        });
      }
      if (source.line) {
        const content = runGit(realRoot, ['show', object]);
        if (content.status !== 0) evidenceFailure('repository-evidence/file-unreadable', `${where}をリビジョン${revision}で読み取れませんでした。`, {
          subject: { path: where, componentId: component.id },
          evidence: { sourcePath: source.path, revision },
          supportedFixes: ['固定済みblobがローカルチェックアウトで読み取り可能か確認する'],
        });
        const lineCount = sourceLineCount(content.stdout);
        const requestedLine = source.endLine || source.line;
        if (requestedLine > lineCount) {
          evidenceFailure('repository-evidence/line-out-of-range', `/components/${componentIndex}/sources/${sourceIndex}は行${requestedLine}を要求していますが、${source.path}はリビジョン${revision}で${lineCount}行です。`, {
            subject: { path: `/components/${componentIndex}/sources/${sourceIndex}`, componentId: component.id },
            evidence: { sourcePath: source.path, requestedLine, lineCount, revision },
            supportedFixes: ['固定済みリビジョンに存在する行範囲を使用する'],
          });
        }
      }
      verified.push({ ...source, href: sourceHref(repository.url.replace(/\.git\/?$/i, '').replace(/\/$/, ''), revision, source) });
      referenceCount += 1;
    }
    nodes[component.id] = verified;
  }
  if (referenceCount === 0) {
    evidenceFailure('repository-evidence/source-required', '/meta/repositoryには1件以上のコンポーネントソース参照が必要です。', {
      subject: { path: '/meta/repository' },
      supportedFixes: ['検証済みコンポーネントソースを1件以上追加するか、repositoryメタデータを削除する'],
    });
  }

  return {
    schemaVersion: 1,
    verified: true,
    repository: {
      url: repository.url.replace(/\.git\/?$/i, '').replace(/\/$/, ''),
      revision,
      shortRevision: revision.slice(0, 7),
    },
    referenceCount,
    nodes,
  };
}

import fs from 'node:fs';
import path from 'node:path';

const MAX_SYMLINK_DEPTH = 64;
const directorySemanticsCache = new Map();
let semanticsProbeSequence = 0;

function splitAbsolute(absolutePath) {
  const root = path.parse(absolutePath).root;
  return {
    root,
    segments: absolutePath.slice(root.length).split(path.sep).filter(Boolean),
  };
}

function canonicalize(targetPath, depth) {
  const absolutePath = path.resolve(targetPath);
  const { root, segments } = splitAbsolute(absolutePath);
  let current = root;

  for (let index = 0; index < segments.length; index += 1) {
    const candidate = path.join(current, segments[index]);
    let stat;
    try {
      stat = fs.lstatSync(candidate);
    } catch (error) {
      if (error.code === 'ENOENT' || error.code === 'ENOTDIR') {
        return path.resolve(current, ...segments.slice(index));
      }
      throw error;
    }

    if (stat.isSymbolicLink()) {
      if (depth >= MAX_SYMLINK_DEPTH) {
        const error = new Error(`シンボリックリンクの循環に "${candidate}" が含まれるため、パスを解決できませんでした。`);
        error.code = 'ELOOP';
        error.path = candidate;
        throw error;
      }
      const link = fs.readlinkSync(candidate);
      const linkTarget = path.isAbsolute(link) ? link : path.resolve(path.dirname(candidate), link);
      return canonicalize(path.join(linkTarget, ...segments.slice(index + 1)), depth + 1);
    }

    current = fs.realpathSync.native(candidate);
  }

  return path.normalize(current);
}

export function canonicalFuturePath(targetPath) {
  try {
    return canonicalize(targetPath, 0);
  } catch (error) {
    if (error?.code !== 'ELOOP') throw error;
    const output = path.resolve(targetPath);
    throw new OutputPathError(`出力パスにシンボリックリンクの循環があります: "${output}"。`, {
      code: 'output/symlink-cycle',
      message: 'シンボリックリンクの循環が含まれるため、出力パスを解決できませんでした。',
      subject: { output },
      evidence: {
        systemCode: 'ELOOP',
        ...(error.path ? { cycleAt: path.resolve(error.path) } : {}),
      },
      supportedFixes: ['シンボリックリンクの循環を削除するか、その外部の出力パスを選択する'],
    });
  }
}

function hasFileIdentity(stat) {
  return stat.ino !== 0 && stat.ino !== 0n;
}

function sameFileIdentity(left, right) {
  return hasFileIdentity(left)
    && hasFileIdentity(right)
    && left.dev === right.dev
    && left.ino === right.ino;
}

function nearestExistingDirectory(targetPath) {
  let directory = path.dirname(targetPath);
  while (true) {
    try {
      const stat = fs.statSync(directory);
      if (stat.isDirectory()) {
        return {
          path: fs.realpathSync.native(directory),
          stat,
        };
      }
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') return null;
    }
    const parent = path.dirname(directory);
    if (parent === directory) return null;
    directory = parent;
  }
}

function directoryIdentityKey(directory) {
  if (!hasFileIdentity(directory.stat)) return null;
  return `${directory.stat.dev}:${directory.stat.ino}`;
}

function probeNamesAlias(directoryPath, authoredName, lookupName) {
  let fileDescriptor;
  let created = false;
  let result = null;
  let cleaned = true;
  const authoredPath = path.join(directoryPath, authoredName);
  const lookupPath = path.join(directoryPath, lookupName);
  try {
    fileDescriptor = fs.openSync(authoredPath, 'wx', 0o600);
    created = true;
    fs.closeSync(fileDescriptor);
    fileDescriptor = undefined;

    let authored;
    let lookup;
    try {
      authored = fs.statSync(authoredPath);
      lookup = fs.statSync(lookupPath);
    } catch (error) {
      if (error.code === 'ENOENT') result = false;
    }
    if (authored && lookup) {
      if (sameFileIdentity(authored, lookup)) {
        result = true;
      } else {
        try {
          result = fs.realpathSync.native(authoredPath) === fs.realpathSync.native(lookupPath);
        } catch {
          result = null;
        }
      }
    }
  } catch {
    result = null;
  } finally {
    if (fileDescriptor !== undefined) {
      try {
        fs.closeSync(fileDescriptor);
      } catch {
        cleaned = false;
      }
    }
    if (created) {
      try {
        fs.unlinkSync(authoredPath);
      } catch {
        cleaned = false;
      }
    }
  }
  return cleaned ? result : null;
}

function probeDirectorySemantics(directory) {
  const cacheKey = directoryIdentityKey(directory);
  if (cacheKey && directorySemanticsCache.has(cacheKey)) {
    return directorySemanticsCache.get(cacheKey);
  }

  semanticsProbeSequence += 1;
  const suffix = `${process.pid}-${Date.now().toString(36)}-${semanticsProbeSequence}`;
  const caseAuthored = `.archify-Case-Probe-${suffix}`;
  const normalizationAuthored = `.archify-norm-\u00e9-probe-${suffix}`;
  const semantics = {
    caseInsensitive: probeNamesAlias(
      directory.path,
      caseAuthored,
      caseAuthored.toLowerCase(),
    ),
    normalizationInsensitive: probeNamesAlias(
      directory.path,
      normalizationAuthored,
      normalizationAuthored.normalize('NFD'),
    ),
  };
  if (
    cacheKey
    && semantics.caseInsensitive !== null
    && semantics.normalizationInsensitive !== null
  ) {
    directorySemanticsCache.set(cacheKey, semantics);
  }
  return semantics;
}

function sameDirectory(left, right) {
  return left.path === right.path || sameFileIdentity(left.stat, right.stat);
}

function futurePathsAlias(leftPath, rightPath) {
  const left = canonicalFuturePath(leftPath);
  const right = canonicalFuturePath(rightPath);
  if (left === right) return true;

  const leftDirectory = nearestExistingDirectory(left);
  const rightDirectory = nearestExistingDirectory(right);
  if (!leftDirectory || !rightDirectory || !sameDirectory(leftDirectory, rightDirectory)) {
    return false;
  }

  const semantics = probeDirectorySemantics(leftDirectory);
  let comparableLeft = path.relative(leftDirectory.path, left);
  let comparableRight = path.relative(rightDirectory.path, right);
  if (semantics.normalizationInsensitive !== false) {
    comparableLeft = comparableLeft.normalize('NFC');
    comparableRight = comparableRight.normalize('NFC');
  }
  if (semantics.caseInsensitive !== false) {
    comparableLeft = comparableLeft.toLowerCase();
    comparableRight = comparableRight.toLowerCase();
  }
  return comparableLeft === comparableRight;
}

export function pathsAlias(leftPath, rightPath) {
  if (futurePathsAlias(leftPath, rightPath)) return true;
  try {
    const left = fs.statSync(leftPath);
    const right = fs.statSync(rightPath);
    return sameFileIdentity(left, right);
  } catch {
    return false;
  }
}

function pathIsInside(directoryPath, targetPath) {
  const relative = path.relative(canonicalFuturePath(directoryPath), canonicalFuturePath(targetPath));
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

export class OutputPathError extends Error {
  constructor(message, diagnostic) {
    super(message);
    this.name = 'OutputPathError';
    this.archifyDiagnostics = [{
      severity: 'error',
      subject: {},
      evidence: {},
      supportedFixes: [],
      ...diagnostic,
    }];
  }
}

export function resolveOutputPath({
  requestedOutput,
  authoredOutput,
  defaultOutput,
  inputPaths = [],
  inputDescription = '入力',
  otherOutputPaths = [],
  cwd = process.cwd(),
}) {
  const rawOutput = requestedOutput || authoredOutput || defaultOutput;
  const source = requestedOutput ? 'cli' : (authoredOutput ? 'meta' : 'default');
  if (
    source === 'meta'
    && (path.isAbsolute(rawOutput) || path.posix.isAbsolute(rawOutput) || path.win32.isAbsolute(rawOutput))
  ) {
    throw new OutputPathError('meta.outputは相対パスでなければなりません。', {
      code: 'output/meta-absolute',
      message: 'meta.outputには現在の作業ディレクトリを基準とする相対パスを指定してください。',
      subject: { output: rawOutput },
      supportedFixes: ['meta.outputを現在の作業ディレクトリ内の相対.htmlパスに設定する'],
    });
  }
  if (source === 'meta' && path.extname(rawOutput).toLowerCase() !== '.html') {
    throw new OutputPathError('meta.outputは.htmlファイルを対象にする必要があります。', {
      code: 'output/meta-extension',
      message: 'meta.outputは.htmlファイルを対象にする必要があります。',
      subject: { output: rawOutput },
      supportedFixes: ['meta.outputを.htmlで終わるパスへ変更する'],
    });
  }
  const outputPath = path.resolve(cwd, rawOutput);
  if (source === 'meta' && path.extname(canonicalFuturePath(outputPath)).toLowerCase() !== '.html') {
    throw new OutputPathError('meta.outputの解決先は.htmlファイルでなければなりません。', {
      code: 'output/meta-resolved-extension',
      message: 'シンボリックリンクの解決後も、meta.outputは.htmlファイルを指す必要があります。',
      subject: { output: rawOutput },
      supportedFixes: ['シンボリックリンクの別名を削除するか、現在の作業ディレクトリ内の.html対象を指すよう変更する'],
    });
  }
  if (source === 'meta' && !pathIsInside(cwd, outputPath)) {
    throw new OutputPathError('meta.outputは現在の作業ディレクトリ内に収める必要があります。', {
      code: 'output/meta-outside-cwd',
      message: 'シンボリックリンクの解決後も、meta.outputは現在の作業ディレクトリ内に収める必要があります。',
      subject: { output: rawOutput, cwd: path.resolve(cwd) },
      supportedFixes: ['meta.outputを現在の作業ディレクトリ内の相対.htmlパスに設定する'],
    });
  }

  for (const inputPath of inputPaths) {
    if (!pathsAlias(outputPath, inputPath)) continue;
    throw new OutputPathError(`出力で${inputDescription}を置き換えてはいけません。`, {
      code: 'output/input-alias',
      message: `シンボリックリンクや将来パスの別名を介する場合も含め、出力で${inputDescription}を置き換えてはいけません。`,
      subject: { output: outputPath, input: path.resolve(inputPath) },
      supportedFixes: ['すべての入力パスと異なる出力パスを選択する'],
    });
  }
  for (const otherOutputPath of otherOutputPaths) {
    if (!pathsAlias(outputPath, otherOutputPath)) continue;
    throw new OutputPathError('出力対象には互いに異なるパスを使用する必要があります。', {
      code: 'output/target-alias',
      message: 'シンボリックリンクや将来パスの別名を含め、出力対象には互いに異なるパスを使用する必要があります。',
      subject: { output: outputPath, conflictingOutput: path.resolve(otherOutputPath) },
      supportedFixes: ['生成する各出力に異なるパスを選択する'],
    });
  }

  return {
    outputPath,
    source,
  };
}

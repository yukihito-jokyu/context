import { spawnSync } from 'node:child_process';
import path from 'node:path';

const OPENERS = {
  darwin: {
    command: 'open',
    method: 'open',
    args: (target) => [target],
  },
  linux: {
    command: 'xdg-open',
    method: 'xdg-open',
    args: (target) => [target],
  },
  win32: {
    command: 'powershell.exe',
    method: 'powershell',
    // Keep the command constant and pass the target through PowerShell's
    // argument array. Paths are never interpolated into executable source.
    args: (target) => [
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      'Start-Process -FilePath $args[0]',
      target,
    ],
  },
};

function launchTarget(target, options = {}) {
  const platform = options.platform || process.platform;
  const opener = OPENERS[platform];
  if (!opener) {
    return {
      requested: true,
      status: 'unsupported',
      target,
      method: null,
    };
  }

  const spawn = options.spawn || spawnSync;
  let result;
  try {
    result = spawn(opener.command, opener.args(target), {
      encoding: 'utf8',
      shell: false,
      stdio: 'ignore',
      timeout: options.timeoutMs || 5000,
      windowsHide: true,
    });
  } catch {
    result = { error: new Error('オープナーで例外が発生しました') };
  }

  let status = 'opened';
  if (result?.error?.code === 'ENOENT') status = 'unsupported';
  else if (result?.error || result?.signal || result?.status !== 0) status = 'failed';

  return {
    requested: true,
    status,
    target,
    method: opener.method,
  };
}

export function openArtifact(target, options = {}) {
  return launchTarget(path.resolve(target), options);
}

export function openLoopbackUrl(target, options = {}) {
  let url;
  try {
    url = new URL(target);
  } catch {
    throw new TypeError('プレビュー URL は有効なループバック HTTP URL である必要があります。');
  }
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port) {
    throw new TypeError('プレビュー URL は http://127.0.0.1:<port> を使用するループバック URL である必要があります。');
  }
  if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new TypeError('プレビュー URL はループバックのプレビュー・ルートを指す必要があります。');
  }
  return launchTarget(url.href, options);
}

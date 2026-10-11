import React from 'react';
import type {ComponentProps} from 'react';
import OriginalA from '@theme-original/MDXComponents/A';
import useBaseUrl from '@docusaurus/useBaseUrl';

// Markdown stays Markdown: a #download fragment requests the original file.
// A native anchor keeps the router from treating artifacts as documentation.
export default function ArtifactAnchor(props: ComponentProps<typeof OriginalA>) {
  const href = typeof props.href === 'string'
    ? props.href.replace(/^pathname:\/\//, '')
    : props.href;
  const artifact = typeof href === 'string' && href.startsWith('/examples/');
  const resolvedHref = useBaseUrl(artifact ? href : '');
  if (artifact) {
    if (resolvedHref.endsWith('#download')) {
      const url = resolvedHref.slice(0, -'#download'.length);
      return <a {...props} href={url} download={decodeURIComponent(url.split('/').pop()!.split('?')[0])} />;
    }
    return <a {...props} href={resolvedHref} target="_blank" rel="noopener noreferrer" />;
  }
  return <OriginalA {...props} />;
}

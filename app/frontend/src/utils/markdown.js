import { marked } from 'marked';
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
  'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'em', 'strong',
  'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'span', 'div', 'details', 'summary', 'figure', 'figcaption',
];

const ALLOWED_ATTR = ['href', 'src', 'alt', 'class', 'id', 'target', 'rel', 'loading'];

export function renderMarkdown(text) {
  if (!text) return '';
  return DOMPurify.sanitize(
    marked(text, { breaks: true, gfm: true }),
    { ALLOWED_TAGS, ALLOWED_ATTR },
  );
}

export { ALLOWED_TAGS, ALLOWED_ATTR };

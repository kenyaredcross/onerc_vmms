import DOMPurify from "dompurify";

const ALLOWED_TAGS = [
  "b",
  "i",
  "em",
  "strong",
  "u",
  "s",
  "p",
  "br",
  "hr",
  "ul",
  "ol",
  "li",
  "span",
  "div",
  "a",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "blockquote",
  "pre",
  "code",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
];


const ALLOWED_ATTR = ["href", "target", "rel", "class"];

export function sanitizeHtml(dirty: string | null | undefined): string {
  if (!dirty) return "";
  return DOMPurify.sanitize(String(dirty), {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
  });
}

export function sanitizeRichHtml(dirty: string | null | undefined): string {
  if (!dirty) return "";
  return DOMPurify.sanitize(String(dirty));
}

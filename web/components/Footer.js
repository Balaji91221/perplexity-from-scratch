// Subtle footer with brand line + links. Shown on the home view.

import { BRAND } from "../lib/constants";
import { BrandMark } from "./icons";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-brand">
        <BrandMark size={14} />
        <span>{BRAND.name}</span>
      </div>
      <div className="footer-meta">
        <span>{BRAND.tagline}</span>
        <span className="footer-dot">·</span>
        <a
          href="https://github.com/anthropics/claude-code"
          target="_blank"
          rel="noreferrer"
          className="footer-link"
        >
          Built with Claude
        </a>
      </div>
    </footer>
  );
}

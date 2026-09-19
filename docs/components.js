const LOGO_SVG = `<svg width="28" height="28" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#d97706"/><path d="M32 14 A18 18 0 0 0 32 50 Z" fill="#FFFFFF"/><line x1="14" y1="26" x2="32" y2="26" stroke="#d97706" stroke-width="3"/><line x1="14" y1="38" x2="32" y2="38" stroke="#d97706" stroke-width="3"/><line x1="32" y1="26" x2="49" y2="26" stroke="#FFFFFF" stroke-width="3"/><line x1="32" y1="38" x2="49" y2="38" stroke="#FFFFFF" stroke-width="3"/><circle cx="32" cy="32" r="18" fill="none" stroke="#FFFFFF" stroke-width="4"/></svg>`;

class SiteHeader extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `<header>
  <a class="logo" href="./index.html">${LOGO_SVG}Klima<span>zwilling</span></a>
  <a class="header-tag" href="./about.html">Über das Projekt</a>
</header>`;
  }
}

class SiteFooter extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `<footer>
  <div class="footer-left">
    <span class="footer-sources">Daten: <a href="https://www.worldclim.org" target="_blank" rel="noopener">WorldClim 2.1</a> · <a href="https://www.geonames.org" target="_blank" rel="noopener">GeoNames</a> · CMIP6 SSP2-4.5</span>
  </div>
  <nav class="footer-nav">
    <a href="./about.html">Über das Projekt</a>
    <a href="./legal.html">Impressum</a>
    <a href="./privacy.html">Datenschutz</a>
  </nav>
</footer>`;
  }
}

customElements.define('site-header', SiteHeader);
customElements.define('site-footer', SiteFooter);

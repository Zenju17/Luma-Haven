<template>
  <section id="location" class="loc-panel" aria-labelledby="location-heading">
    <div class="loc">
      <div class="loc-text">
        <h2 id="location-heading">A quiet street in Daun Penh</h2>
        <p>Luma Haven sits on a tree-lined lane in Phnom Penh's historic Daun Penh district, within walking distance of cafes, bookshops and the riverside.</p>

        <dl class="loc-rules">
          <div><dt>Check-in and check-out</dt><dd>From 14:00 and by 12:00 (Asia/Phnom_Penh). Free luggage storage at reception.</dd></div>
          <div><dt>Quiet hours</dt><dd>22:00 to 07:00 in corridors and courtyards.</dd></div>
          <div><dt>Smoking</dt><dd>All rooms, indoor spaces and balconies are smoke-free.</dd></div>
          <div><dt>Room keys</dt><dd>Leave your key at the front desk when you go out and collect it when you return.</dd></div>
        </dl>

        <ul class="loc-contact">
          <li><span>Email</span><a href="mailto:hello@luma.local">hello@luma.local</a></li>
          <li><span>Front desk</span><a href="tel:+85500000000">+855 00 000 000</a></li>
          <li><span>Address</span>Daun Penh, Phnom Penh, Cambodia</li>
        </ul>
      </div>

      <figure class="loc-map">
        <svg viewBox="0 0 480 420" role="img" aria-labelledby="map-title map-desc">
          <title id="map-title">Map of the area around Luma Haven</title>
          <desc id="map-desc">Luma Haven is a short walk from the Royal Palace and riverside and the National Museum of Cambodia. The airport is a 35-minute drive away.</desc>
          <rect width="480" height="420" fill="var(--palm-leaf)" />
          <path d="M0 40 C 120 20, 200 90, 300 70 S 440 20, 480 50 L480 130 C 400 150, 330 120, 260 150 S 100 130, 0 110 Z" fill="color-mix(in oklab, var(--river) 15%, transparent)" />
          <g stroke="color-mix(in oklab, var(--silt) 40%, transparent)" stroke-width="3" fill="none" stroke-linecap="round">
            <path d="M20 250 H460" /><path d="M20 330 H460" /><path d="M110 160 V410" /><path d="M250 160 V410" /><path d="M380 160 V410" /><path d="M110 250 L250 190" />
          </g>
          <g font-family="Manrope, sans-serif" font-size="13" font-weight="600">
            <g transform="translate(150 92)"><rect x="-6" y="-14" width="198" height="28" rx="14" fill="var(--paper)" stroke="var(--rule)" /><text x="8" y="5" fill="var(--river)">Royal Palace &amp; Riverside</text></g>
            <g transform="translate(250 210)"><rect x="-6" y="-14" width="216" height="28" rx="14" fill="var(--paper)" stroke="var(--rule)" /><text x="8" y="5" fill="var(--river)">National Museum of Cambodia</text></g>
            <g transform="translate(40 380)"><rect x="-6" y="-14" width="400" height="28" rx="14" fill="var(--paper)" stroke="var(--rule)" /><text x="8" y="5" fill="var(--river)">Phnom Penh International Airport, 35 min drive</text></g>
            <circle cx="250" cy="250" r="11" fill="var(--river)" />
            <circle cx="250" cy="250" r="18" fill="none" stroke="var(--river)" stroke-opacity=".35" />
            <text x="272" y="288" fill="var(--river)">Luma Haven</text>
          </g>
        </svg>
        <figcaption>Not to scale. Royal Palace and riverside are about 10 minutes on foot; the National Museum about 8.</figcaption>
      </figure>
    </div>
  </section>
</template>

<style scoped>
.loc-panel { margin-bottom: 1rem; padding: clamp(1.25rem, 3vw, 2.5rem); background: var(--paper); border-radius: var(--radius-panel); }
.loc { display: grid; gap: 2rem; }
.loc-text { display: grid; gap: 1.25rem; align-content: start; }
.loc-text h2 { font-size: clamp(2rem, 4vw, 3rem); color: var(--ink); }
.loc-text > p { color: var(--silt); }
.loc-rules { display: grid; gap: 1rem; }
.loc-rules > div { display: grid; gap: .15rem; padding-top: .75rem; border-top: 1px solid var(--rule); }
.loc-rules dt { font-weight: 600; color: var(--river); }
.loc-rules dd { color: var(--silt); font-size: .9375rem; }
.loc-contact { display: grid; gap: .5rem; padding-top: .75rem; border-top: 1px solid var(--rule); font-size: .9375rem; color: var(--river); }
.loc-contact span { display: inline-block; min-width: 6rem; color: var(--silt); }
.loc-contact a { text-decoration: underline; }
.loc-map svg { width: 100%; height: auto; border-radius: var(--radius-photo); display: block; }
.loc-map figcaption { margin-top: .5rem; color: var(--silt); font-size: .875rem; }
@media (min-width: 1000px) { .loc { grid-template-columns: 1fr 1fr; gap: 3rem; align-items: start; } }
</style>

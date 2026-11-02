// Builds `srcset` strings so grids download small WebP variants while lightboxes
// and HiDPI screens get the full-resolution original.
//
// - Static photos: variants listed in data/imageVariants.json, produced by
//   scripts/build_static_image_variants.py.
// - Database media (/api/v1/media/...): the server renders `<name>.w<width>.webp`
//   on first request, so only the original width (from the API) is needed.
import manifest from '../data/imageVariants.json'

const VARIANT_WIDTHS = [640, 1280] as const
const DB_MEDIA_PREFIX = '/api/v1/media/'

type ManifestEntry = { width: number; variants: number[] }
const staticImages = manifest as Record<string, ManifestEntry>

/** Typical `sizes` hints for the layouts used across the guest site. */
export const SIZES = {
  card: '(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw',
  wide: '(min-width: 1024px) 60vw, 100vw',
  full: '100vw',
  lightbox: '(min-width: 1152px) 1152px, 100vw',
  thumb: '160px',
} as const

export function responsiveSrcset(src: string | null | undefined, width?: number | null): string | undefined {
  if (!src) return undefined
  const entry = staticImages[src]
  if (entry) {
    return [...entry.variants.map((w) => `${src}.w${w}.webp ${w}w`), `${src} ${entry.width}w`].join(', ')
  }
  if (src.startsWith(DB_MEDIA_PREFIX) && width && width > 0) {
    const widths = VARIANT_WIDTHS.filter((w) => w < width)
    return [...widths.map((w) => `${src}.w${w}.webp ${w}w`), `${src} ${width}w`].join(', ')
  }
  return undefined
}

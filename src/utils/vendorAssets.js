/** 收银台脚本随站点发布，避免客户浏览器访问外部静态域名失败。 */
export const AIRWALLEX_ELEMENTS_SDK = '/vendor/airwallex-elements.bundle.min.js'

export function loadLocalScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      if (existing.dataset.loaded === 'true') resolve()
      else {
        existing.addEventListener('load', resolve, { once: true })
        existing.addEventListener('error', reject, { once: true })
      }
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.addEventListener('load', () => {
      script.dataset.loaded = 'true'
      resolve()
    }, { once: true })
    script.addEventListener('error', reject, { once: true })
    document.head.appendChild(script)
  })
}

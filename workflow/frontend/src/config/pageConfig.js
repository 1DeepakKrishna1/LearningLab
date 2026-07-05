import roleConfigs from './pageConfig.json'

export const VISIBILITY = {
  HIDE:    'hide',
  ENABLE:  'enable',
  DISABLE: 'disable',
}

export function getPageConfig(role) {
  return roleConfigs[role] ?? roleConfigs.org_user
}

export function isVisible(role, page, action) {
  const cfg = getPageConfig(role)
  return cfg?.[page]?.[action] !== VISIBILITY.HIDE
}

export function isEnabled(role, page, action) {
  const cfg = getPageConfig(role)
  const val = cfg?.[page]?.[action]
  return val === VISIBILITY.ENABLE
}

import roleConfigs from './sidebarConfig.json'

export const VISIBILITY = {
  HIDE:    'hide',
  ENABLE:  'enable',
  DISABLE: 'disable',
}

export function getSidebarConfig(role) {
  return roleConfigs[role] ?? roleConfigs.org_user
}

// Metadata config for drill-down sections - drives tabs, columns, and contextual filters

export const FILTER_DETAIL_CONFIG = {
  Workflows: {
    accent: 'indigo',
    tabs: [
      { id: 'total_workflows',  label: 'Total Workflows'  },
      { id: 'active_workflows', label: 'Active Workflows' },
      { id: 'draft_workflows',  label: 'Draft Workflows'  },
    ],
    columns: [
      { key: 'name',             label: 'Workflow Name',  sortable: true  },
      { key: 'status',           label: 'Status',         sortable: true,  type: 'status'   },
      { key: 'version',          label: 'Version',        sortable: false                   },
      { key: 'created_by',       label: 'Created By',     sortable: true                    },
      { key: 'last_updated',     label: 'Last Updated',   sortable: true,  type: 'datetime' },
      { key: 'last_run',         label: 'Last Run',       sortable: true,  type: 'datetime' },
      { key: 'total_executions', label: 'Executions',     sortable: true,  type: 'number'   },
      { key: 'success_rate',     label: 'Success Rate',   sortable: true,  type: 'pct'      },
      { key: 'avg_duration',     label: 'Avg Duration',   sortable: true,  type: 'duration' },
    ],
    contextFilters: [
      { key: 'status', label: 'Status', options: [
        { value: '', label: 'All Status' },
        { value: 'active', label: 'Active' },
        { value: 'draft', label: 'Draft' },
        { value: 'archived', label: 'Archived' },
      ]},
    ],
  },
  Executions: {
    accent: 'emerald',
    tabs: [
      { id: 'total_executions', label: 'Total Executions' },
      { id: 'running',          label: 'Running'          },
      { id: 'completed',        label: 'Completed'        },
      { id: 'failed',           label: 'Failed'           },
    ],
    columns: [
      { key: 'id',            label: 'Execution ID',  sortable: true                    },
      { key: 'workflow_name', label: 'Workflow',       sortable: true                    },
      { key: 'status',        label: 'Status',         sortable: true,  type: 'status'   },
      { key: 'started_at',    label: 'Start Time',     sortable: true,  type: 'datetime' },
      { key: 'ended_at',      label: 'End Time',       sortable: true,  type: 'datetime' },
      { key: 'duration',      label: 'Duration',       sortable: true,  type: 'duration' },
      { key: 'tokens_used',   label: 'Tokens Used',    sortable: true,  type: 'number'   },
      { key: 'sla_status',    label: 'SLA Status',     sortable: false, type: 'sla'      },
    ],
    contextFilters: [
      { key: 'status', label: 'Status', options: [
        { value: '', label: 'All Status' },
        { value: 'running', label: 'Running' },
        { value: 'completed', label: 'Completed' },
        { value: 'failed', label: 'Failed' },
        { value: 'pending', label: 'Pending' },
      ]},
      { key: 'sla_breach', label: 'SLA', options: [
        { value: '', label: 'All' },
        { value: 'yes', label: 'SLA Breach' },
        { value: 'no', label: 'Within SLA' },
      ]},
    ],
  },
  Performance: {
    accent: 'purple',
    tabs: [
      { id: 'avg_duration',    label: 'Avg Duration'   },
      { id: 'sla_compliance',  label: 'SLA Compliance' },
      { id: 'success_rate',    label: 'Success Rate'   },
    ],
    columns: [
      { key: 'name',               label: 'Workflow',        sortable: true                   },
      { key: 'avg_duration_s',     label: 'Avg Duration',    sortable: true, type: 'duration_s' },
      { key: 'sla_compliance_pct', label: 'SLA Compliance',  sortable: true, type: 'pct'      },
      { key: 'success_rate',       label: 'Success Rate',    sortable: true, type: 'pct'      },
      { key: 'total_runs',         label: 'Total Runs',      sortable: true, type: 'number'   },
      { key: 'failed_runs',        label: 'Failed Runs',     sortable: true, type: 'number'   },
    ],
    contextFilters: [],
  },
  Tokens: {
    accent: 'amber',
    tabs: [
      { id: 'token_usage',       label: 'Token Usage'                    },
      { id: 'token_trend',       label: 'Token Trend'                    },
      { id: 'token_by_workflow', label: 'Token Consumption by Workflow'  },
      { id: 'token_by_agent',    label: 'Token Consumption by Agent'     },
    ],
    columns: [
      { key: 'name',        label: 'Name',         sortable: true                  },
      { key: 'type',        label: 'Type',         sortable: true                  },
      { key: 'tokens_used', label: 'Tokens Used',  sortable: true, type: 'number' },
      { key: 'cost_usd',    label: 'Cost (USD)',   sortable: true, type: 'cost'   },
      { key: 'pct_budget',  label: '% of Budget',  sortable: true, type: 'pct'   },
    ],
    contextFilters: [],
  },
  Trends: {
    accent: 'cyan',
    tabs: [
      { id: 'execution_trend',   label: 'Execution Trend'   },
      { id: 'usage_trend',       label: 'Usage Trend'       },
      { id: 'failure_trend',     label: 'Failure Trend'     },
      { id: 'performance_trend', label: 'Performance Trend' },
    ],
    columns: [
      { key: 'day',        label: 'Date',          sortable: true                  },
      { key: 'count',      label: 'Count',         sortable: true, type: 'number' },
      { key: 'change_pct', label: 'Change',        sortable: true, type: 'change' },
      { key: 'total',      label: 'Running Total', sortable: false, type: 'number' },
    ],
    contextFilters: [],
  },
  Library: {
    accent: 'violet',
    tabs: [
      { id: 'tools',     label: 'Tools'     },
      { id: 'agents',    label: 'Agents'    },
      { id: 'templates', label: 'Templates' },
    ],
    columns: [
      { key: 'name',          label: 'Name',        sortable: true                    },
      { key: 'type',          label: 'Type',         sortable: true                   },
      { key: 'description',   label: 'Description',  sortable: false                  },
      { key: 'review_status', label: 'Status',       sortable: true, type: 'rstatus' },
      { key: 'usage_count',   label: 'Usage',        sortable: true, type: 'number'  },
    ],
    contextFilters: [
      { key: 'review_status', label: 'Status', options: [
        { value: '', label: 'All Status' },
        { value: 'approved', label: 'Approved' },
        { value: 'pending', label: 'Pending' },
        { value: 'rejected', label: 'Rejected' },
      ]},
    ],
  },
  Users: {
    accent: 'sky',
    tabs: [
      { id: 'platform_users', label: 'Platform Users' },
      { id: 'active_users',   label: 'Active Users'   },
      { id: 'user_activity',  label: 'User Activity'  },
      { id: 'top_consumers',  label: 'Top Consumers'  },
    ],
    columns: [
      { key: 'name',                 label: 'User Name',            sortable: true                    },
      { key: 'role',                 label: 'Role',                 sortable: true                    },
      { key: 'active_workflows',     label: 'Active Workflows',     sortable: true, type: 'number'   },
      { key: 'executions_triggered', label: 'Executions Triggered', sortable: true, type: 'number'   },
      { key: 'token_usage',          label: 'Token Usage',          sortable: true, type: 'number'   },
      { key: 'last_active',          label: 'Last Active',          sortable: true, type: 'datetime' },
    ],
    contextFilters: [
      { key: 'role', label: 'Role', options: [
        { value: '', label: 'All Roles' },
        { value: 'product_admin', label: 'Product Admin' },
        { value: 'process_admin', label: 'Process Admin' },
        { value: 'org_user', label: 'Org User' },
        { value: 'cust_user', label: 'Customer User' },
        { value: 'cust_admin', label: 'Customer Admin' },
      ]},
    ],
  },
}

export const ACCENT_COLORS = {
  indigo: { chip: 'bg-indigo-600 text-white',   chipOff: 'bg-slate-800 text-indigo-300 border border-indigo-500/30', tab: 'border-indigo-500 text-indigo-300', text: 'text-indigo-400' },
  emerald: { chip: 'bg-emerald-600 text-white',  chipOff: 'bg-slate-800 text-emerald-300 border border-emerald-500/30', tab: 'border-emerald-500 text-emerald-300', text: 'text-emerald-400' },
  purple: { chip: 'bg-purple-600 text-white',   chipOff: 'bg-slate-800 text-purple-300 border border-purple-500/30', tab: 'border-purple-500 text-purple-300', text: 'text-purple-400' },
  amber:  { chip: 'bg-amber-600 text-white',    chipOff: 'bg-slate-800 text-amber-300 border border-amber-500/30', tab: 'border-amber-500 text-amber-300', text: 'text-amber-400' },
  cyan:   { chip: 'bg-cyan-600 text-white',     chipOff: 'bg-slate-800 text-cyan-300 border border-cyan-500/30', tab: 'border-cyan-500 text-cyan-300', text: 'text-cyan-400' },
  violet: { chip: 'bg-violet-600 text-white',   chipOff: 'bg-slate-800 text-violet-300 border border-violet-500/30', tab: 'border-violet-500 text-violet-300', text: 'text-violet-400' },
  sky:    { chip: 'bg-sky-600 text-white',      chipOff: 'bg-slate-800 text-sky-300 border border-sky-500/30', tab: 'border-sky-500 text-sky-300', text: 'text-sky-400' },
}

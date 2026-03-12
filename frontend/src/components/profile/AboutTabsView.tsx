import type { AboutTab } from '../../types/profile'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'

export default function AboutTabsView({ tabs }: { tabs: AboutTab[] }) {
  if (!tabs || tabs.length === 0) return null

  return (
    <div className="bg-white dark:bg-dark-card rounded-xl border border-gray-200 dark:border-dark-border p-5">
      <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-4">Raw About Tabs Data</h3>
      <div className="space-y-2">
        {tabs.map((tab, i) => (
          <TabAccordion key={i} tab={tab} />
        ))}
      </div>
    </div>
  )
}

function TabAccordion({ tab }: { tab: AboutTab }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border border-gray-100 dark:border-dark-border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-dark-surface rounded-lg"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {tab.name || 'Tab'}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-3">
          {tab.sections.map((section, j) => (
            <div key={j} className="pl-4 border-l-2 border-gray-200 dark:border-dark-border">
              <p className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">{section.title}</p>
              {section.fields.map((field, k) => (
                <div key={k} className="mb-2">
                  {field.text && <p className="text-sm text-gray-800 dark:text-gray-200">{field.text}</p>}
                  {field.field_type && (
                    <span className="text-[10px] bg-gray-100 dark:bg-dark-surface px-1.5 py-0.5 rounded text-gray-500 dark:text-gray-400">
                      {field.field_type}
                    </span>
                  )}
                  {field.details.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {field.details.map((d, l) => (
                        <li key={l} className="text-xs text-gray-500 dark:text-gray-400">• {d}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
              {section.fields.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-gray-500 italic">No data</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

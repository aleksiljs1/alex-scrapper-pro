import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link2, Loader2 } from 'lucide-react'
import { useAddProfile } from '../../hooks/useProfiles'

export default function ProfileForm() {
  const [url, setUrl] = useState('')
  const addProfile = useAddProfile()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    addProfile.mutate(url.trim(), {
      onSuccess: () => {
        setUrl('')
        navigate('/')
      },
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Facebook Profile URL
        </label>
        <div className="relative">
          <Link2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            id="url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.facebook.com/username"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-dark-border rounded-lg text-sm bg-white dark:bg-dark-card dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 dark:placeholder-gray-500"
            disabled={addProfile.isPending}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Enter a Facebook profile URL or username. Examples: https://www.facebook.com/johndoe or johndoe
        </p>
      </div>

      <button
        type="submit"
        disabled={addProfile.isPending || !url.trim()}
        className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {addProfile.isPending && <Loader2 size={16} className="animate-spin" />}
        {addProfile.isPending ? 'Adding...' : 'Add to Queue'}
      </button>
    </form>
  )
}

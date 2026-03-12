import ProfileForm from '../components/profile/ProfileForm'

export default function AddProfilePage() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Add Profile to Queue</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Enter a Facebook profile URL to start scraping. The profile will be added to the
          processing queue.
        </p>
      </div>
      <ProfileForm />
    </div>
  )
}

export default function ErrorMessage({ message, onClose }) {
  if (!message) return null

  return (
    <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
      <p className="text-red-800 text-sm">{message}</p>
      {onClose && (
        <button
          onClick={onClose}
          className="text-red-600 underline text-sm mt-2"
        >
          Dismiss
        </button>
      )}
    </div>
  )
}

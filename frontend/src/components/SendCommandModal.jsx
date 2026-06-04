export default function SendCommandModal({ device_id, onClose, onSuccess }) {
  return (
    <div data-testid="send-command-modal" className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">Send Command</h2>
        <p className="text-sm text-gray-600 mb-4">Device: {device_id}</p>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 border rounded-lg hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

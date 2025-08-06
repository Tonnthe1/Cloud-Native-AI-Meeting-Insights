'use client'
import { useRef } from "react"
import axios from "axios"

export default function UploadPage() {
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file) return alert('Please select a file')

    const formData = new FormData()
    formData.append('file', file)

    await axios.post(
      "http://localhost:8000/upload-audio", 
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
          "x-api-key": process.env.NEXT_PUBLIC_API_KEY, 
        }
      }
    )
    alert('Upload success')
  }

  return (
    <div>
      <h1>Upload Meeting Audio</h1>
      <input type="file" ref={fileRef} accept="audio/*"/>
      <button onClick={handleUpload}>Upload</button>
    </div>
  )
}

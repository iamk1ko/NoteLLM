export const formatBytes = (size: number) => {
  if (size === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  return `${(size / 1024 ** index).toFixed(1)} ${units[index]}`
}

export const formatStatus = (status: number) => {
  switch (status) {
    case 0:
      return { label: '上传中', type: 'waiting' }
    case 1:
      return { label: '已上传', type: 'success' }
    case 2:
      return { label: '已向量化', type: 'success' }
    case 3:
      return { label: '失败', type: 'error' }
    default:
      return { label: '未知', type: 'waiting' }
  }
}

export const formatDateTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export const getMimeType = (file: File) => {
  if (file.type) return file.type
  const name = file.name.toLowerCase()
  if (name.endsWith('.md') || name.endsWith('.markdown')) return 'text/markdown'
  if (name.endsWith('.txt')) return 'text/plain'
  if (name.endsWith('.pdf')) return 'application/pdf'
  if (name.endsWith('.doc')) return 'application/msword'
  if (name.endsWith('.docx'))
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  return 'application/octet-stream'
}

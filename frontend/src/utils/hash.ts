import SparkMD5 from 'spark-md5'

export const hashFile = (file: File, chunkSize = 4 * 1024 * 1024) =>
  new Promise<string>((resolve, reject) => {
    const spark = new SparkMD5.ArrayBuffer()
    const reader = new FileReader()
    let currentChunk = 0
    const totalChunks = Math.ceil(file.size / chunkSize)

    const loadNext = () => {
      const start = currentChunk * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      reader.readAsArrayBuffer(file.slice(start, end))
    }

    reader.onload = (event) => {
      if (!event.target?.result) return
      spark.append(event.target.result as ArrayBuffer)
      currentChunk += 1
      if (currentChunk < totalChunks) {
        loadNext()
      } else {
        resolve(spark.end())
      }
    }

    reader.onerror = () => reject(new Error('文件读取失败'))

    loadNext()
  })

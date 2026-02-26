from enum import Enum, unique


@unique
class RedisKey(str, Enum):
    FILE_STORAGE_METADATA = "file_storage:meta:{}:{}"
    UPLOAD_FILE_CHUNKS_BITMAP = "upload:bitmap:{}:{}"
    FILE_VECTORIZATION_TASK_STATUS = "vector:task:{}"
    FILE_VECTORIZATION_TASK_ERROR = "vector:task:error:{}"
    FILE_VECTORIZATION_TASK_STAGE = "vector:task:stage:{}"
    FILE_VECTORIZATION_TASK_ERROR_CODE = "vector:task:error:code:{}"
    FILE_VECTORIZATION_TASK_ERROR_MESSAGE = "vector:task:error:message:{}"
    FILE_VECTORIZATION_TASK_RETRYABLE = "vector:task:retryable:{}"
    FILE_VECTORIZATION_TASK_UPDATED_AT = "vector:task:updated_at:{}"
    FILE_VECTORIZATION_TASK_CURSOR = "vector:cursor:{}"
    USER_SESSION = "auth:session:{}"  # {} 填写 session_id
    # Chat Memory - 短期记忆 (Redis List，滑动窗口)
    CHAT_SESSION_MESSAGES = "chat:session:{}:messages"  # {} 填写 session_id
    # Chat Memory - 缓存标记 (用于标记该会话是否已加载过完整历史)
    CHAT_SESSION_CACHE_FLAG = "chat:session:{}:cached"  # {} 填写 session_id


@unique
class MilvusField(str, Enum):
    PK = "pk"
    FILE_ID = "file_id"
    FILE_MD5 = "file_md5"
    CHUNK_INDEX = "chunk_index"
    PAGE_NO = "page_no"
    SECTION = "section"
    CONTENT = "content"
    SPARSE_VECTOR = "sparse_vector"
    DENSE_VECTOR = "dense_vector"
    METADATA = "metadata"

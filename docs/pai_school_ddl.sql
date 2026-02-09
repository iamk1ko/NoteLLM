CREATE DATABASE IF NOT EXISTS pai_school
    CHARACTER SET = utf8mb4
    COLLATE = utf8mb4_general_ci;

USE pai_school;

-- 用户表
-- 先删除表再创建，避免报错
drop table if exists users;
create table if not exists users
(
    id             int unsigned auto_increment comment 'ID,主键'
        primary key,
    username       varchar(20)                                         not null comment '用户名',
    password       varchar(255)                                        not null comment '密码hash',
    name           varchar(10)                                         not null comment '姓名',
    role           varchar(20)      default 'user'                     not null comment '用户角色：user-普通用户，admin-管理员',
    status         tinyint unsigned default 1                          not null comment '用户状态：1-正常，2-禁用，3-删除',
    gender         tinyint unsigned default 3                          not null comment '性别, 1:男, 2:女, 3:保密',
    phone          char(11)                                            null comment '手机号',
    email          varchar(50)                                         null comment '电子邮箱',
    avatar_file_id bigint unsigned                                     null comment '头像文件ID,关联file_storage表ID(不建外键)',
    bio            varchar(255)     default '这个人很懒,什么都没写...' null comment '个人简介',
    create_time    datetime         default CURRENT_TIMESTAMP          null comment '创建时间',
    update_time    datetime                                            null comment '修改时间',
    constraint phone
        unique (phone),
    constraint username
        unique (username),
    index idx_avatar_file_id (avatar_file_id),
    index idx_role (role),
    index idx_status (status),
    index idx_create_time (create_time)
)
    comment '用户表';

# 聊天会话表和消息表
drop table if exists chat_session;
CREATE TABLE IF NOT EXISTS chat_session
(
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '会话ID',
    user_id     INT UNSIGNED NOT NULL COMMENT '用户ID，对应users表',
    biz_type    VARCHAR(50)  NOT NULL COMMENT '业务类型（如：ai_chat, customer_service, pdf_qa 等）',
    title       VARCHAR(255) DEFAULT NULL COMMENT '会话标题，如：和AI助手的对话',
    context_id  VARCHAR(64)  DEFAULT NULL COMMENT '外部上下文ID，如PDF文档ID',
    status      TINYINT      DEFAULT 1 COMMENT '会话状态（1:正常, 0:删除）',
    create_time DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_biz (user_id, biz_type),
    INDEX idx_user_created (user_id, create_time),
    INDEX idx_user_status (user_id, status)
) COMMENT ='聊天会话表';

drop table if exists chat_message;
CREATE TABLE IF NOT EXISTS chat_message
(
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '消息ID',
    session_id  BIGINT UNSIGNED                           NOT NULL COMMENT '会话ID，对应chat_session.id',
    user_id     INT UNSIGNED                              NOT NULL COMMENT '所属用户ID',
    role        ENUM ('user','assistant','system','tool') NOT NULL COMMENT '消息角色',
    content     TEXT                                      NOT NULL COMMENT '消息内容',
    model_name  VARCHAR(100) DEFAULT NULL COMMENT '使用的模型（如 gpt-4o, qwen-2 等）',
    token_count INT          DEFAULT NULL COMMENT '本次消息的token数',
    create_time DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session (session_id),
    INDEX idx_session_time (session_id, create_time),
    INDEX idx_session_id (session_id, id),
    INDEX idx_user (user_id)
) COMMENT ='聊天消息表';

drop table if exists chat_context;
CREATE TABLE IF NOT EXISTS chat_context
(
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id     BIGINT UNSIGNED NOT NULL COMMENT '会话ID，对应chat_session.id',
    reference_id   VARCHAR(128)  DEFAULT NULL COMMENT '上下文引用对象ID（如PDF文件ID或向量chunk ID）',
    reference_text TEXT COMMENT '命中的文本片段内容',
    similarity     DECIMAL(6, 4) DEFAULT NULL COMMENT '相似度',
    create_time    DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    INDEX idx_session (session_id),
    INDEX idx_session_time (session_id, create_time)
) COMMENT ='聊天上下文引用表';

-- 文件存储表
drop table if exists file_storage;
CREATE TABLE IF NOT EXISTS `file_storage`
(
    `id`              BIGINT UNSIGNED AUTO_INCREMENT COMMENT '文件ID，主键'
        PRIMARY KEY,
    `user_id`         INT UNSIGNED                               NOT NULL COMMENT '上传用户ID，关联users表',
    `filename`        VARCHAR(255)                               NOT NULL COMMENT '原始文件名',
    `bucket_name`     VARCHAR(100)                               NOT NULL COMMENT 'MinIO存储桶名称',
    `object_name`     VARCHAR(255)                               NOT NULL COMMENT 'MinIO中的对象名称（完整路径）',
    `content_type`    VARCHAR(100)                               NOT NULL COMMENT '文件MIME类型（如：image/jpeg、application/pdf）',
    `file_size`       BIGINT UNSIGNED                            NOT NULL COMMENT '文件大小（字节）',
    `etag`            VARCHAR(100)                               NULL COMMENT 'MinIO返回的文件唯一标识（用于校验文件完整性）',
    `is_public`       TINYINT(1)       DEFAULT 0                 NOT NULL COMMENT '是否为公共文件：1-公共，0-私有',
    `status`          TINYINT UNSIGNED DEFAULT 1                 NOT NULL COMMENT '文件状态：1-可用，2-已删除，3-禁用',
    `chat_session_id` bigint unsigned                            null comment '所属于哪一个会话id',
    `upload_time`     DATETIME         DEFAULT CURRENT_TIMESTAMP NULL COMMENT '上传时间',
    `update_time`     DATETIME                                   NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_public` (`is_public`),
    INDEX `idx_user_public` (`user_id`, `is_public`),
    INDEX `idx_bucket_object` (`bucket_name`, `object_name`),
    INDEX `idx_chat_session_id` (`chat_session_id`)
)
    COMMENT '文件存储表（MinIO文件元数据）';

-- 文件分片/切片表（用于分片上传文件）
drop table if exists file_chunks;
CREATE TABLE `file_chunks`
(
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `file_id`     BIGINT                DEFAULT NULL COMMENT '所属文件ID（合并成功后回填）',
    `file_md5`    VARCHAR(64)  NOT NULL COMMENT '文件MD5，用于上传会话标识',
    `chunk_index` INT          NOT NULL COMMENT '分片索引，从0开始',
    `chunk_size`  INT          NOT NULL COMMENT '分片大小（字节）',
    `etag`        VARCHAR(100)          DEFAULT NULL COMMENT '分片ETag/MD5',
    `bucket_name` VARCHAR(100) NOT NULL COMMENT '临时桶名称',
    `object_name` VARCHAR(255) NOT NULL COMMENT '分片对象名称',
    `status`      INT          NOT NULL DEFAULT 1 COMMENT '分片状态：0-上传中，1-已上传，2-已合并，3-失败',
    `create_time` DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    `update_time` DATETIME(6)           DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_file_md5_chunk_index` (`file_md5`, `chunk_index`),
    KEY `idx_file_id` (`file_id`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  ROW_FORMAT = DYNAMIC COMMENT ='文件分片表（file_chunks）';

-- 语义切片与向量表（rag_chunks）
drop table if exists rag_chunks;
CREATE TABLE `rag_chunks`
(
    `id`           BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `file_id`      BIGINT      NOT NULL COMMENT '所属文件ID（file_storage.id）',
    `chunk_index`  INT         NOT NULL COMMENT '语义切片索引，从0开始',
    `chunk_text`   MEDIUMTEXT  NOT NULL COMMENT '切片文本内容',
    `chunk_tokens` INT         NOT NULL COMMENT '切片token数量',
    `page_no`      INT                  DEFAULT NULL COMMENT '页码（PDF等）',
    `section`      VARCHAR(255)         DEFAULT NULL COMMENT '章节/标题',
    `embedding_id` VARCHAR(128)         DEFAULT NULL COMMENT '向量库中的embedding标识',
    `status`       INT         NOT NULL DEFAULT 1 COMMENT '切片状态：1-有效，2-删除，3-失败',
    `create_time`  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    `update_time`  DATETIME(6)          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_file_id` (`file_id`),
    KEY `idx_file_chunk` (`file_id`, `chunk_index`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  ROW_FORMAT = DYNAMIC COMMENT ='语义切片与向量表（rag_chunks）';


-- 会话-文件关联表
drop table if exists chat_session_files;
CREATE TABLE `chat_session_files`
(
    `id`              BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `chat_session_id` BIGINT      NOT NULL COMMENT '会话ID，关联chat_session.id',
    `file_id`         BIGINT      NOT NULL COMMENT '文件ID，关联file_storage.id',
    `create_time`     DATETIME(6) NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '关联时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_session_file` (`chat_session_id`, `file_id`),
    KEY `idx_chat_session_id` (`chat_session_id`),
    KEY `idx_file_id` (`file_id`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
    COMMENT ='会话-文件关联表（chat_session_files）';

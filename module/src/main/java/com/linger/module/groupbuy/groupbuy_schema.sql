-- 高并发拼团交易引擎 PostgreSQL 结构
-- 执行前请确认连接的是 Tool Hub 使用的同一个 PostgreSQL 数据库。
-- 该脚本可重复执行，只负责建表和索引，不包含测试数据。

CREATE TABLE IF NOT EXISTS groupbuy_activities (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    sku_id VARCHAR(64) NOT NULL,
    unit_price NUMERIC(19, 2) NOT NULL CHECK (unit_price >= 0),
    total_stock INTEGER NOT NULL CHECK (total_stock >= 0),
    per_user_limit INTEGER NOT NULL DEFAULT 1 CHECK (per_user_limit > 0),
    target_count INTEGER NOT NULL CHECK (target_count > 0),
    pay_timeout_seconds BIGINT NOT NULL DEFAULT 900 CHECK (pay_timeout_seconds > 0),
    group_timeout_seconds BIGINT NOT NULL DEFAULT 86400 CHECK (group_timeout_seconds > 0),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'READY',
    version BIGINT NOT NULL DEFAULT 0,
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_groupbuy_activity_time CHECK (ends_at > starts_at),
    CONSTRAINT ck_groupbuy_activity_status CHECK (status IN ('READY', 'RUNNING', 'ENDED', 'CLOSED'))
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_activities_status_time
    ON groupbuy_activities (status, starts_at, ends_at);

COMMENT ON TABLE groupbuy_activities IS '拼团活动定义表';
COMMENT ON COLUMN groupbuy_activities.id IS '活动主键';
COMMENT ON COLUMN groupbuy_activities.name IS '活动名称';
COMMENT ON COLUMN groupbuy_activities.sku_id IS '参与拼团的商品 SKU 编码';
COMMENT ON COLUMN groupbuy_activities.unit_price IS '活动单价，单位为元';
COMMENT ON COLUMN groupbuy_activities.total_stock IS '活动初始总库存';
COMMENT ON COLUMN groupbuy_activities.per_user_limit IS '单个用户在活动内的限购数量';
COMMENT ON COLUMN groupbuy_activities.target_count IS '每个团的目标成团人数';
COMMENT ON COLUMN groupbuy_activities.pay_timeout_seconds IS '订单支付超时时间，单位为秒';
COMMENT ON COLUMN groupbuy_activities.group_timeout_seconds IS '开团后允许成团的最长时间，单位为秒';
COMMENT ON COLUMN groupbuy_activities.starts_at IS '活动开始时间';
COMMENT ON COLUMN groupbuy_activities.ends_at IS '活动结束时间';
COMMENT ON COLUMN groupbuy_activities.status IS '活动状态：READY待发布、RUNNING进行中、ENDED已结束、CLOSED已关闭';
COMMENT ON COLUMN groupbuy_activities.version IS '乐观锁版本号';
COMMENT ON COLUMN groupbuy_activities.created_by IS '创建人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_activities.updated_by IS '最后修改人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_activities.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_activities.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_groups (
    id BIGSERIAL PRIMARY KEY,
    activity_id BIGINT NOT NULL REFERENCES groupbuy_activities(id),
    creator_user_id BIGINT NOT NULL,
    target_count INTEGER NOT NULL CHECK (target_count > 0),
    reserved_count INTEGER NOT NULL DEFAULT 0 CHECK (reserved_count >= 0),
    paid_count INTEGER NOT NULL DEFAULT 0 CHECK (paid_count >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'INIT',
    expire_at TIMESTAMPTZ NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_groupbuy_group_status CHECK (status IN ('INIT', 'OPEN', 'SUCCESS', 'FAILED', 'CLOSED')),
    CONSTRAINT ck_groupbuy_group_count CHECK (paid_count <= reserved_count AND reserved_count <= target_count)
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_groups_activity_status_expire
    ON groupbuy_groups (activity_id, status, expire_at);

COMMENT ON TABLE groupbuy_groups IS '拼团实例表';
COMMENT ON COLUMN groupbuy_groups.id IS '团主键';
COMMENT ON COLUMN groupbuy_groups.activity_id IS '所属拼团活动ID';
COMMENT ON COLUMN groupbuy_groups.creator_user_id IS '开团用户ID';
COMMENT ON COLUMN groupbuy_groups.target_count IS '目标成团人数快照';
COMMENT ON COLUMN groupbuy_groups.reserved_count IS '当前占用团名额的人数，包含未支付和已支付成员';
COMMENT ON COLUMN groupbuy_groups.paid_count IS '已支付人数';
COMMENT ON COLUMN groupbuy_groups.status IS '团状态：INIT初始化、OPEN可参团、SUCCESS已成团、FAILED成团失败、CLOSED已关闭';
COMMENT ON COLUMN groupbuy_groups.expire_at IS '成团截止时间';
COMMENT ON COLUMN groupbuy_groups.version IS '乐观锁版本号';
COMMENT ON COLUMN groupbuy_groups.created_by IS '创建人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_groups.updated_by IS '最后修改人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_groups.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_groups.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_orders (
    id VARCHAR(36) PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    activity_id BIGINT NOT NULL REFERENCES groupbuy_activities(id),
    group_id BIGINT NOT NULL REFERENCES groupbuy_groups(id),
    sku_id VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(19, 2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(19, 2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    payable_amount NUMERIC(19, 2) NOT NULL CHECK (payable_amount >= 0),
    status VARCHAR(24) NOT NULL DEFAULT 'INIT',
    reject_reason VARCHAR(128),
    reservation_id VARCHAR(36),
    payment_no VARCHAR(64),
    pay_deadline TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 0,
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_groupbuy_orders_user_request UNIQUE (user_id, request_id),
    CONSTRAINT ck_groupbuy_order_status CHECK (status IN (
        'INIT', 'WAIT_PAY', 'PAID', 'GROUP_SUCCESS', 'COMPLETED',
        'REJECTED', 'CANCELLED', 'REFUNDING', 'REFUNDED'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_groupbuy_orders_payment_no
    ON groupbuy_orders (payment_no) WHERE payment_no IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_groupbuy_orders_group_status
    ON groupbuy_orders (group_id, status);
CREATE INDEX IF NOT EXISTS idx_groupbuy_orders_status_deadline
    ON groupbuy_orders (status, pay_deadline);

COMMENT ON TABLE groupbuy_orders IS '拼团交易订单表';
COMMENT ON COLUMN groupbuy_orders.id IS '订单UUID';
COMMENT ON COLUMN groupbuy_orders.request_id IS '客户端请求幂等号';
COMMENT ON COLUMN groupbuy_orders.user_id IS '下单用户ID';
COMMENT ON COLUMN groupbuy_orders.activity_id IS '拼团活动ID';
COMMENT ON COLUMN groupbuy_orders.group_id IS '参与的团ID';
COMMENT ON COLUMN groupbuy_orders.sku_id IS '商品SKU编码快照';
COMMENT ON COLUMN groupbuy_orders.quantity IS '购买数量';
COMMENT ON COLUMN groupbuy_orders.unit_price IS '下单时活动单价快照';
COMMENT ON COLUMN groupbuy_orders.discount_amount IS '优惠总金额';
COMMENT ON COLUMN groupbuy_orders.payable_amount IS '订单应付金额';
COMMENT ON COLUMN groupbuy_orders.status IS '订单状态：INIT初始化、WAIT_PAY待支付、PAID已支付、GROUP_SUCCESS已成团、COMPLETED已完成、REJECTED已拒绝、CANCELLED已取消、REFUNDING退款中、REFUNDED已退款';
COMMENT ON COLUMN groupbuy_orders.reject_reason IS '下单被拒绝或补偿关闭的原因';
COMMENT ON COLUMN groupbuy_orders.reservation_id IS 'Redis库存和名额预占标识';
COMMENT ON COLUMN groupbuy_orders.payment_no IS '支付渠道流水号';
COMMENT ON COLUMN groupbuy_orders.pay_deadline IS '支付截止时间';
COMMENT ON COLUMN groupbuy_orders.paid_at IS '支付完成时间';
COMMENT ON COLUMN groupbuy_orders.version IS '乐观锁版本号';
COMMENT ON COLUMN groupbuy_orders.created_by IS '创建人用户ID，通常等于下单用户ID';
COMMENT ON COLUMN groupbuy_orders.updated_by IS '最后修改人用户ID，0表示系统任务或回调';
COMMENT ON COLUMN groupbuy_orders.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_orders.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_members (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES groupbuy_groups(id),
    user_id BIGINT NOT NULL,
    order_id VARCHAR(36) NOT NULL REFERENCES groupbuy_orders(id),
    status VARCHAR(20) NOT NULL DEFAULT 'RESERVED',
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_groupbuy_members_group_user UNIQUE (group_id, user_id),
    CONSTRAINT uq_groupbuy_members_order UNIQUE (order_id),
    CONSTRAINT ck_groupbuy_member_status CHECK (status IN (
        'RESERVED', 'PAID', 'CONFIRMED', 'CANCELLED', 'REFUNDING', 'REFUNDED'
    ))
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_members_group_status
    ON groupbuy_members (group_id, status);

COMMENT ON TABLE groupbuy_members IS '拼团成员及成员状态表';
COMMENT ON COLUMN groupbuy_members.id IS '成员记录主键';
COMMENT ON COLUMN groupbuy_members.group_id IS '团ID';
COMMENT ON COLUMN groupbuy_members.user_id IS '成员用户ID';
COMMENT ON COLUMN groupbuy_members.order_id IS '成员对应订单ID';
COMMENT ON COLUMN groupbuy_members.status IS '成员状态：RESERVED已占位、PAID已支付、CONFIRMED已成团确认、CANCELLED已取消、REFUNDING退款中、REFUNDED已退款';
COMMENT ON COLUMN groupbuy_members.created_by IS '创建人用户ID';
COMMENT ON COLUMN groupbuy_members.updated_by IS '最后修改人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_members.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_members.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_inventory_ledger (
    id BIGSERIAL PRIMARY KEY,
    activity_id BIGINT NOT NULL REFERENCES groupbuy_activities(id),
    sku_id VARCHAR(64) NOT NULL,
    order_id VARCHAR(36) NOT NULL REFERENCES groupbuy_orders(id),
    operation VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_groupbuy_inventory_ledger_order_operation UNIQUE (order_id, operation),
    CONSTRAINT ck_groupbuy_inventory_operation CHECK (operation IN ('RESERVE', 'CONFIRM', 'RELEASE', 'REFUND'))
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_inventory_activity_sku
    ON groupbuy_inventory_ledger (activity_id, sku_id, created_at);

COMMENT ON TABLE groupbuy_inventory_ledger IS '拼团库存操作流水表，用于幂等和对账';
COMMENT ON COLUMN groupbuy_inventory_ledger.id IS '库存流水主键';
COMMENT ON COLUMN groupbuy_inventory_ledger.activity_id IS '拼团活动ID';
COMMENT ON COLUMN groupbuy_inventory_ledger.sku_id IS '商品SKU编码';
COMMENT ON COLUMN groupbuy_inventory_ledger.order_id IS '触发库存变化的订单ID';
COMMENT ON COLUMN groupbuy_inventory_ledger.operation IS '库存操作：RESERVE预占、CONFIRM确认、RELEASE释放、REFUND退款返还';
COMMENT ON COLUMN groupbuy_inventory_ledger.quantity IS '本次库存变化数量，恒为正数，方向由operation决定';
COMMENT ON COLUMN groupbuy_inventory_ledger.created_by IS '创建人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_inventory_ledger.updated_by IS '最后修改人用户ID，库存流水通常不修改';
COMMENT ON COLUMN groupbuy_inventory_ledger.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_inventory_ledger.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_outbox_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(40) NOT NULL,
    aggregate_type VARCHAR(32) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retry_count INTEGER NOT NULL DEFAULT 0,
    locked_by VARCHAR(64),
    locked_until TIMESTAMPTZ,
    last_error VARCHAR(500),
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_groupbuy_outbox_status CHECK (status IN ('PENDING', 'PROCESSING', 'DONE', 'DEAD'))
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_outbox_poll
    ON groupbuy_outbox_events (status, available_at, locked_until);

COMMENT ON TABLE groupbuy_outbox_events IS '拼团本地事务消息表';
COMMENT ON COLUMN groupbuy_outbox_events.id IS '事件UUID';
COMMENT ON COLUMN groupbuy_outbox_events.event_type IS '事件类型';
COMMENT ON COLUMN groupbuy_outbox_events.aggregate_type IS '聚合类型，如ORDER或GROUP';
COMMENT ON COLUMN groupbuy_outbox_events.aggregate_id IS '聚合业务主键';
COMMENT ON COLUMN groupbuy_outbox_events.payload IS '事件扩展数据JSON';
COMMENT ON COLUMN groupbuy_outbox_events.status IS '处理状态：PENDING待处理、PROCESSING处理中、DONE已完成、DEAD死信';
COMMENT ON COLUMN groupbuy_outbox_events.available_at IS '下一次允许处理的时间';
COMMENT ON COLUMN groupbuy_outbox_events.retry_count IS '已失败重试次数';
COMMENT ON COLUMN groupbuy_outbox_events.locked_by IS '当前抢占事件的工作节点';
COMMENT ON COLUMN groupbuy_outbox_events.locked_until IS '工作节点租约截止时间';
COMMENT ON COLUMN groupbuy_outbox_events.last_error IS '最近一次处理错误摘要';
COMMENT ON COLUMN groupbuy_outbox_events.created_by IS '创建人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_outbox_events.updated_by IS '最后修改人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_outbox_events.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_outbox_events.updated_at IS '最后修改时间';

CREATE TABLE IF NOT EXISTS groupbuy_delay_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    business_id VARCHAR(64) NOT NULL,
    execute_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    worker_id VARCHAR(64),
    locked_until TIMESTAMPTZ,
    last_error VARCHAR(500),
    created_by BIGINT NOT NULL DEFAULT 0,
    updated_by BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_groupbuy_delay_task_business UNIQUE (task_type, business_id),
    CONSTRAINT ck_groupbuy_delay_task_status CHECK (status IN ('PENDING', 'CLAIMED', 'RUNNING', 'DONE', 'DEAD'))
);

CREATE INDEX IF NOT EXISTS idx_groupbuy_delay_task_poll
    ON groupbuy_delay_tasks (status, execute_at, locked_until);

COMMENT ON TABLE groupbuy_delay_tasks IS '拼团可靠延迟任务表';
COMMENT ON COLUMN groupbuy_delay_tasks.id IS '延迟任务主键';
COMMENT ON COLUMN groupbuy_delay_tasks.task_type IS '任务类型：PAYMENT_TIMEOUT支付超时、GROUP_TIMEOUT拼团超时';
COMMENT ON COLUMN groupbuy_delay_tasks.business_id IS '任务关联业务主键';
COMMENT ON COLUMN groupbuy_delay_tasks.execute_at IS '计划执行时间';
COMMENT ON COLUMN groupbuy_delay_tasks.status IS '任务状态：PENDING待调度、CLAIMED已装载、RUNNING执行中、DONE已完成、DEAD死信';
COMMENT ON COLUMN groupbuy_delay_tasks.retry_count IS '已失败重试次数';
COMMENT ON COLUMN groupbuy_delay_tasks.worker_id IS '当前抢占任务的工作节点';
COMMENT ON COLUMN groupbuy_delay_tasks.locked_until IS '工作节点租约截止时间';
COMMENT ON COLUMN groupbuy_delay_tasks.last_error IS '最近一次执行错误摘要';
COMMENT ON COLUMN groupbuy_delay_tasks.created_by IS '创建人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_delay_tasks.updated_by IS '最后修改人用户ID，0表示系统';
COMMENT ON COLUMN groupbuy_delay_tasks.created_at IS '创建时间';
COMMENT ON COLUMN groupbuy_delay_tasks.updated_at IS '最后修改时间';

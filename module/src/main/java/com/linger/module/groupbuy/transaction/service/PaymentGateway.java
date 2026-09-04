package com.linger.module.groupbuy.transaction.service;

import com.linger.module.groupbuy.transaction.entity.GroupBuyOrderEntity;

public interface PaymentGateway {
    boolean refund(GroupBuyOrderEntity order);
}


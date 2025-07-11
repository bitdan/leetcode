package com.linger;

import org.junit.jupiter.api.Test;

import javax.crypto.SecretKeyFactory;

/**
 * @version 1.0
 * @description TestAlgorithm
 * @date 2024/11/4 14:26:55
 */
public class TestAlgorithm {

    @Test
    public void test() {
        try {
            String algorithm = "PBEWithHmacSHA512AndAES_256";
            SecretKeyFactory factory = SecretKeyFactory.getInstance(algorithm);
            System.out.println(algorithm + " is supported.");
        } catch (Exception e) {
            System.out.println("Algorithm not supported: " + e.getMessage());
        }
    }
}

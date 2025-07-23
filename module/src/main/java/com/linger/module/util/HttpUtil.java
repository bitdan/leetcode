package com.linger.module.util;

import lombok.extern.slf4j.Slf4j;
import okhttp3.*;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * @version 1.0
 * @description HttpUtil
 * @date 2025/5/7 18:35:52
 */
@Slf4j
public class HttpUtil {

    private static final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();

    private static final MediaType JSON = MediaType.parse("application/json; charset=utf-8");

    public static Response doGet(String url, Map<String, String> headers) throws IOException {
        Request.Builder builder = new Request.Builder().url(url);

        // 添加请求头
        if (headers != null) {
            headers.forEach(builder::addHeader);
        }

        Request request = builder.build();

        return client.newCall(request).execute();
    }

    public static Response doPost(String url, Map<String, String> headers, String body) throws IOException {
        RequestBody requestBody = RequestBody.create(body, JSON);

        Request.Builder builder = new Request.Builder()
                .url(url)
                .post(requestBody);

        if (headers != null) {
            headers.forEach(builder::addHeader);
        }

        Request request = builder.build();

        return client.newCall(request).execute();
    }

    public static Response doPut(String url, Map<String, String> headers, String body) throws IOException {
        RequestBody requestBody = RequestBody.create(body, JSON);

        Request.Builder builder = new Request.Builder()
                .url(url)
                .put(requestBody);

        if (headers != null) {
            headers.forEach(builder::addHeader);
        }

        Request request = builder.build();

        return client.newCall(request).execute();
    }

}

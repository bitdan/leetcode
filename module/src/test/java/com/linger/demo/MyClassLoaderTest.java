package com.linger.demo;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * @description MyClassLoaderTest
 * @date 2026/2/24 17:40:21
 * @version 1.0
 */
public class MyClassLoaderTest {
    // 自定义类加载器
    static class MyClassLoader extends ClassLoader {

        private String classPath;

        public MyClassLoader(String classPath) {
            this.classPath = classPath;
        }

        @Override
        protected Class<?> findClass(String name) throws ClassNotFoundException {
            try {
                // 读取 class 文件字节
                byte[] bytes = Files.readAllBytes(
                        Paths.get(classPath + "/" + name.replace(".", "/") + ".class")
                );
                return defineClass(name, bytes, 0, bytes.length);
            } catch (IOException e) {
                throw new ClassNotFoundException(name);
            }
        }

        @Override
        public Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {

            synchronized (getClassLoadingLock(name)) {

                // 1️⃣ 先检查是否已加载
                Class<?> c = findLoadedClass(name);

                if (c == null) {

                    // 2️⃣ java.* 必须父加载
                    if (name.startsWith("java.")) {
                        c = getParent().loadClass(name);
                    } else {

                        try {
                            // 3️⃣ 先自己加载（关键）
                            c = findClass(name);
                        } catch (ClassNotFoundException e) {
                            // 4️⃣ 自己找不到再交给父加载器
                            c = getParent().loadClass(name);
                        }
                    }
                }

                if (resolve) {
                    resolveClass(c);
                }

                return c;
            }
        }
    }

    public static void main(String[] args) throws Exception {

        String classDir = "F:\\project\\leetcode\\jvm";
        MyClassLoader loader1 = new MyClassLoader(classDir);
        MyClassLoader loader2 = new MyClassLoader(classDir);

        Class<?> clazz1 = loader1.loadClass("com.linger.demo.StudentD");
        Class<?> clazz2 = loader2.loadClass("com.linger.demo.StudentD");

        Object obj1 = clazz1.getDeclaredConstructor().newInstance();

        System.out.println("clazz1 == clazz2 ? " + (clazz1 == clazz2));

        System.out.println("clazz1 loader: " + clazz1.getClassLoader());
        System.out.println("clazz2 loader: " + clazz2.getClassLoader());

        // 尝试强转
        try {
            Object casted = clazz2.cast(obj1);
            System.out.println("强转成功: " + casted);
        } catch (ClassCastException e) {
            System.out.println("强转失败: " + e);
        }
    }
}

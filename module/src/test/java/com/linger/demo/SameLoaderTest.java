package com.linger.demo;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * @description SameLoaderTest
 * @date 2026/2/24 18:07:42
 * @version 1.0
 */
public class SameLoaderTest {
    static class MyClassLoader extends ClassLoader {
        private String classPath;

        public MyClassLoader(String classPath) {
            this.classPath = classPath;
        }

        @Override
        protected Class<?> findClass(String name) throws ClassNotFoundException {
            try {
                byte[] bytes = Files.readAllBytes(
                        Paths.get(classPath + "/" + name.replace(".", "/") + ".class")
                );
                return defineClass(name, bytes, 0, bytes.length);
            } catch (IOException e) {
                throw new ClassNotFoundException(name);
            }
        }
    }

    public static void main(String[] args) throws Exception {
        String classDir = "F:\\project\\leetcode\\jvm";
        MyClassLoader loader = new MyClassLoader(classDir);

        Class<?> clazz1 = loader.loadClass("com.linger.demo.StudentD");
        Class<?> clazz2 = loader.loadClass("com.linger.demo.StudentD");

        System.out.println("clazz1 == clazz2 ? " + (clazz1 == clazz2));

        Object obj1 = clazz1.getDeclaredConstructor().newInstance();
        Object obj2 = clazz2.cast(obj1); // 强转成功
        System.out.println("强转成功: " + obj2);
    }
}

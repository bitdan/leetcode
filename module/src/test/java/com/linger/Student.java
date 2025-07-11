package com.linger;

import lombok.extern.slf4j.Slf4j;


/**
 * @version 1.0
 * @description test
 * @date 2024/8/13 14:46:17
 */
@Slf4j
public class Student implements Comparable<Student> {
    public int id;
    public String name;
    public int age;

    @Override
    public String toString() {
        return "Student{id=" + id + ", name='" + name + "', age=" + age + '}';
    }

    Student(){}

    public Student(int i, String ace, int i1) {
        this.id = i;
        this.name = ace;
        this.age = i1;
    }


    @Override
    public int compareTo(Student o) {
        int flag = this.name.compareTo(o.name);
        if (flag == 0) {
            return this.age - o.age;
        }
        return flag;
    }

}

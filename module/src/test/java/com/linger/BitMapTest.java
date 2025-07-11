package com.linger;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;

import java.util.*;
import java.util.stream.Collectors;

/**
 * @version 1.0
 * @description test
 * @date 2024/8/11 23:58:13
 */
@Slf4j
public class BitMapTest {
    static final int MAXIMUM_CAPACITY = 1 << 30;

    @Test
    public void test() {
        int nums[] = {5, 3, 7, 5, 9, 3, 8, 7};
        BitSet bitSet = new BitSet();
        for (int i = 0; i < nums.length; i++) {
            if (!bitSet.get(nums[i])) {
                bitSet.set(nums[i]);
            }
        }
        log.info("bitSet: {}", bitSet);
    }

    @Test
    public void test1() {
        Student ace = new Student(1, "ace", 22);
        Student ace1 = new Student(1, "ace", 23);
        Student ab = new Student(1, "ab", 23);
        Student[] students = {ace, ace1, ab};
        Arrays.sort(students);
        for (Student student : students) {
            log.info("id: " + student.id + ", name: " + student.name + ", age: " + student.age);
        }
    }

    @Test
    public void test2() {
        Student ace = new Student(1, "ace", 22);
        Student ace1 = new Student(1, "ace", 23);
        Student ab = new Student(1, "ab", 23);
        // 将数组转换为List
        List<Student> students = Arrays.asList(ace, ace1, ab);

        // 使用Collections.sort对List进行排序
        Collections.sort(students);

        // 输出排序结果
        log.info("students is : {}", students);
    }

    @Test
    public void test3() {
        Student ace = new Student(1, "ace", 22);
        Student ace1 = new Student(1, "ace", 23);
        Student ab = new Student(1, "ab", 23);
        List<Student> students = Arrays.asList(ace, ace1, ab);
        Collections.sort(students, (o1, o2) -> {
            int i = o1.name.compareTo(o2.name);
            if (i == 0) {
                return Integer.compare(o1.age, o2.age);
            }
            return i;
        });
        log.info("students is : {}", students);
    }

    @Test
    public void test4() {
        Student ace = new Student(1, "ace", 22);
        Student ace1 = new Student(1, "ace", 23);
        Student ab = new Student(1, "ab", 23);
        List<Student> students = new ArrayList<>(Arrays.asList(ace, ace1, ab));
        List<Student> collect = students.stream().sorted().collect(Collectors.toList());
        log.info("students is : {}", collect);

//        Iterator<Student> iterator = students.iterator();
//        while (iterator.hasNext()) {
//            Student student = iterator.next();
//            if (student.name.equals("ab")) {
//                iterator.remove();
//            }
//        }
        students.removeIf(o -> o.name.equals("ab"));
        log.info("students is : {}", students);
    }

    @Test
    public void test5() {
        LruListCache<Student> studentLruListCache = new LruListCache<>(3);
        studentLruListCache.add(new Student(1, "ace", 22));
        studentLruListCache.add(new Student(1, "ace", 23));
        studentLruListCache.add(new Student(1, "ab", 23));
        studentLruListCache.add(new Student(1, "ax", 23));
        log.info("studentLruListCache is : {}", studentLruListCache);

    }

    @Test
    public void test6() {
        int tableSize = tableSizeFor(3);
        log.info("tableSize is : {}", tableSize);
    }

    static final int tableSizeFor(int cap) {
        int n = cap - 1;
        n |= n >>> 1;
        n |= n >>> 2;
        n |= n >>> 4;
        n |= n >>> 8;
        n |= n >>> 16;
        return (n < 0) ? 1 : (n >= MAXIMUM_CAPACITY) ? MAXIMUM_CAPACITY : n + 1;
    }

    @Test
    public void test7() {
        MyHashMap map = new MyHashMap();
        map.put(1, 1);
        map.put(2, 2);
        map.put(1, 40);
        map.put(2, 200);

        log.info(map.get(1).toString());
        log.info(map.get(2).toString());
    }

    @Test
    public void test8() {
        MyHashMap map = new MyHashMap<Integer, Integer>();
        map.put(1, 1);
        map.put(2, 2);
        map.put(1, 40);
        map.put(2, 200);

        log.info(map.get(1).toString());
        log.info(map.get(2).toString());
        Set set = map.keySet();
        log.info(set.toString());
        Set set1 = map.entrySet();
        log.info(set1.toString());
        log.info("map.size() is : {}", map.size());
        HashMap<Object, Object> hashMap = new HashMap<>();

        hashMap.put(1, 1);
        hashMap.put(2, 2);
        hashMap.put(1, 40);
        hashMap.put(2, 200);
        Set<Map.Entry<Object, Object>> entries = hashMap.entrySet();
        log.info("entries is : {}", entries);

    }

    @Test
    public void test9() {
        RedBlackTree<Integer> tree = new RedBlackTree<>();

        tree.insert(7);
        tree.insert(3);
        tree.insert(18);
        tree.insert(10);
        tree.insert(22);
        tree.insert(8);
        tree.insert(11);
        tree.insert(26);
        tree.insert(2);
        tree.insert(6);
        tree.insert(13);

        System.out.println("中序遍历红黑树:");
        tree.inorder();
        tree.printTree();

        tree.delete(18);
        System.out.println("删除18后的中序遍历:");
        tree.inorder();
        tree.printTree();

        tree.delete(11);
        System.out.println("删除11后的中序遍历:");
        tree.inorder();
        tree.printTree();
    }

    @Test
    public void test10() {
        RedBlackTree<Integer> tree = new RedBlackTree<>();

        int[] values = {7, 3, 18, 10, 22, 8, 11, 26, 2, 6, 13};
        for (int value : values) {
            tree.insert(value);
            System.out.println("\n插入 " + value + " 后的树结构:");
            tree.printTree();
        }

        System.out.println("\n中序遍历红黑树:");
        tree.inorder();

        int[] deleteValues = {18, 11, 3};
        for (int value : deleteValues) {
            tree.delete(value);
            System.out.println("\n删除 " + value + " 后的树结构:");
            tree.printTree();
        }
    }

    @Test
    public void test11() {
        BinarySearchTree bst = new BinarySearchTree();
        bst.insert(7);
        bst.insert(3);
        bst.insert(6);
        bst.insert(9);
        bst.insert(4);
        bst.insert(1);
        bst.insert(8);

        int kthSmallest = bst.kthSmallest(4);
        log.info("kthSmallestElement is : {}", kthSmallest);

        System.out.println("===前序");
        bst.preOrderTraverse(bst.getRoot());
        System.out.println();
        System.out.println("===中序");
        bst.inOrderTraverse(bst.getRoot());
        System.out.println();
        System.out.println("===后序");
        bst.postOrderTraverse(bst.getRoot());
        System.out.println();
    }

    @Test
    public void test12() {
        List<String> sensitiveWords = new ArrayList<>();
        sensitiveWords.add("qw");
        sensitiveWords.add("sb");

        Trie filter = new Trie(sensitiveWords);
        boolean result = filter.search("sb");
        System.out.println(result);
    }

    @Test
    public void test13() {
        String str = "aaabbbdcdsasfasfasfbbghjtttwwr";
        int maxNum = getMaxNum(str);
        System.out.println(maxNum);
    }

    public int getMaxNum(String str) {
        if (str == null || str.length() == 0) {
            return 0;
        }
        HashMap<String, Integer> stringIntegerHashMap = new HashMap<>();
        for (int i = 0; i < str.length(); i++) {
            String c = String.valueOf(str.charAt(i));
            if (!stringIntegerHashMap.containsKey(c)) {
                stringIntegerHashMap.put(c, 1);
            } else {
                Integer val = stringIntegerHashMap.get(c);
                val++;
                stringIntegerHashMap.put(c, val);
            }
        }

        Set<Map.Entry<String, Integer>> entries = stringIntegerHashMap.entrySet();
        log.info("entries is : {}", entries);
        int maxNum = 0;
        for (Map.Entry<String, Integer> entry : entries) {
            maxNum = Math.max(maxNum, entry.getValue());
        }
        return maxNum;
    }
}



package com.linger;

/**
 * @version 1.0
 * @description BinarySearchTree
 * @date 2024/8/19 15:53:04
 */
public class BinarySearchTree {
    private TreeNode root;
    private int count = 0; // 计数器
    private int result = Integer.MIN_VALUE; // 查找结果

    public BinarySearchTree() {
    }

    public void insert(int val) {
        root = insertRecursively(root, val);
    }

    private TreeNode insertRecursively(TreeNode root, int val) {
        if (root == null) {
            root = new TreeNode(val);
            return root;
        }
        if (val < root.val) {
            root.left = insertRecursively(root.left, val);
        } else if (val > root.val) {
            root.right = insertRecursively(root.right, val);
        }
        return root;
    }

    private void inOrderTraverse(TreeNode root, int k) {
        if (root == null) return;
        inOrderTraverse(root.left, k);
        count++;
        if (count == k) {
            result = root.val;
            return;
        }
        inOrderTraverse(root.right, k);
    }

    public int kthSmallest(int k) {
        count = 0;
        result = Integer.MIN_VALUE;
        inOrderTraverse(root, k);
        return result;
    }

    public TreeNode getRoot() {
        return root;
    }

    public void preOrderTraverse(TreeNode root) {
        if (root == null) return;
        System.out.print(root.val + " ");
        preOrderTraverse(root.left);
        preOrderTraverse(root.right);
    }


    public void inOrderTraverse(TreeNode root) {
        if (root == null) return;
        inOrderTraverse(root.left);
        System.out.print(root.val + " ");
        inOrderTraverse(root.right);
    }

    public void postOrderTraverse(TreeNode root) {
        if (root == null) return;
        postOrderTraverse(root.left);
        postOrderTraverse(root.right);
        System.out.print(root.val + " ");
    }
}

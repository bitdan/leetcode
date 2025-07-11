package com.linger;

import java.util.List;

/**
 * @version 1.0
 * @description Trie
 * @date 2024/8/19 13:46:20
 */
public class Trie {
    private TrieNode root;

    public Trie() {
        root = new TrieNode();
    }

    public void insert(String word) {
        TrieNode node = root;
        for (char c : word.toCharArray()) {
            node.getChildren().putIfAbsent(c, new TrieNode());
            node = node.getChildren().get(c);
        }
        node.setEndOfWord(true);
    }

    public boolean search(String text) {
        for (int i = 0; i < text.length(); i++) {
            TrieNode node = root;
            int j = i;
            while (j < text.length() && node != null) {
                node = node.getChildren().get(text.charAt(j));
                if (node != null && node.isEndOfWord()) {
                    return true;
                }
                j++;
            }
        }
        return false;
    }

    public Trie(List<String> sensitiveWords) {
        this();
        for (String word : sensitiveWords) {
            insert(word);
        }
    }
}

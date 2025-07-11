package com.linger.demo;

import java.util.HashMap;
import java.util.Map;

/**
 * @version 1.0
 * @description trienode
 * @date 2024/8/19 13:44:18
 */
public class TrieNode {
    private Map<Character, TrieNode> children;
    private boolean isEndOfWord;

    public TrieNode() {
        children = new HashMap<>();
        isEndOfWord = false;
    }

    public Map<Character, TrieNode> getChildren() {
        return children;
    }

    public Boolean isEndOfWord() {
        return isEndOfWord;
    }

    public void setEndOfWord(boolean isEndOfWord) {
        this.isEndOfWord = isEndOfWord;
    }
}

package com.linger.module.pdf;

/**
 * @version 1.0
 * @description PdfTextExtractor
 * @date 2025/7/9 14:42:29
 */

import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.InputStream;
import java.net.URL;
import java.util.ArrayList;

@Slf4j
public class PdfTextExtractor {

    public static void extractTextFromUrl(String url, String postalCode) {
        ArrayList<Integer> notfoundMatch = new ArrayList<>();
        StringBuilder sb = new StringBuilder();
        try (InputStream in = new URL(url).openStream();
             PDDocument document = PDDocument.load(in)) {

            int totalPages = document.getNumberOfPages();
            log.info("总页数: {}", totalPages);
            for (int page = 1; page <= totalPages; page++) {
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setStartPage(page);
                stripper.setEndPage(page);

                String pageText = stripper.getText(document);
                sb.append(pageText);
                if (!pageText.contains(postalCode)) {
                    notfoundMatch.add(page);
                }
            }

        } catch (Exception e) {
            log.error("提取PDF内容失败:", e);
        } finally {
            log.info("PDF内容: {}", sb);
            log.info("notfoundMatch is : {}", notfoundMatch);
        }
    }

    public static void main(String[] args) {
        String url = "https://img.botaili.com/erp/2026/01/28/FBA15LBJHG76_PackageLabel_A4_4.pdf";
        extractTextFromUrl(url, "63801");
    }
}

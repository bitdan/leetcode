package com.linger.test;

/**
 * @version 1.0
 * @description PdfTextExtractor
 * @date 2025/7/9 14:42:29
 */

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.InputStream;
import java.net.URL;

public class PdfTextExtractor {

    public static String extractTextFromUrl(String pdfUrl) {
        try (InputStream in = new URL(pdfUrl).openStream();
             PDDocument document = PDDocument.load(in)) {

            PDFTextStripper stripper = new PDFTextStripper();
            return stripper.getText(document);

        } catch (Exception e) {
            throw new RuntimeException("提取 PDF 内容失败: " + e.getMessage(), e);
        }
    }

    public static void main(String[] args) {
        String url = "https://img.botaili.com/erp/2025/06/03/FBA15KF64HQM_PackageLabel_Thermal_NonPCP.pdf";
        String text = extractTextFromUrl(url);
        System.out.println("提取内容：\n" + text);
    }
}

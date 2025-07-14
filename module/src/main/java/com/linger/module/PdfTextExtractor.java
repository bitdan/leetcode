package com.linger.module;

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
        try (InputStream in = new URL(url).openStream();
             PDDocument document = PDDocument.load(in)) {

            int totalPages = document.getNumberOfPages();

            for (int page = 1; page <= totalPages; page++) {
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setStartPage(page);
                stripper.setEndPage(page);

                String pageText = stripper.getText(document);
                if (!pageText.contains(postalCode)) {
                    notfoundMatch.add(page);
                }
            }

        } catch (Exception e) {
            log.error("提取PDF内容失败:", e);
        } finally {
            log.info("notfoundMatch is : {}", notfoundMatch);
        }
    }

    public static void main(String[] args) {
        String url = "https://img.botaili.com/erp/2025/06/03/FBA15KF64HQM_PackageLabel_Thermal_NonPCP.pdf";
        extractTextFromUrl(url, "63801");
    }
}

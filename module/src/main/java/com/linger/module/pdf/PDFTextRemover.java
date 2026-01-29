package com.linger.module.pdf;

import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.PDPageContentStream.AppendMode;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Slf4j
public class PDFTextRemover {

    public enum RemoveType {
        SHIP_FROM, SHIP_TO, BOTH
    }

    /**
     * 核心方法：移除 SHIP FROM / SHIP TO 地址
     */
    public static byte[] removeShipInfo(String pdfUrl, RemoveType removeType) throws Exception {
        try (InputStream in = new URL(pdfUrl).openStream();
             PDDocument document = PDDocument.load(in)) {
            log.info("🔍 正在处理 PDF: {}", document.getNumberOfPages());
            List<TextRegion> shipFromRegions = new ArrayList<>();
            List<TextRegion> shipToRegions = new ArrayList<>();

            PDFTextStripper stripper = new PDFTextStripper() {
                int currentPage = 0;
                boolean inShipFromSection = false;
                boolean inShipToSection = false;

                @Override
                protected void startPage(PDPage page) {
                    currentPage = getCurrentPageNo() - 1;
                    inShipFromSection = false;
                    inShipToSection = false;
                    log.info("[P%d] 🔍 正在处理第 %d 页...", currentPage + 1, currentPage + 1);
                }

                @Override
                protected void writeString(String string, List<TextPosition> textPositions) {
                    if (textPositions.isEmpty()) return;

                    String text = string.trim();
                    TextPosition first = textPositions.get(0);
                    TextPosition last = textPositions.get(textPositions.size() - 1);

                    float x1 = first.getXDirAdj();
                    float x2 = last.getXDirAdj() + last.getWidthDirAdj();
                    float y = first.getYDirAdj();

                    // 检测标签

                    if (text.startsWith("SHIP FROM:")) {
                        inShipFromSection = true;
                        log.info("[P%d] 🔍 检测到 SHIP FROM 标签", currentPage + 1);

                    } else if (text.startsWith("SHIP TO:")) {
                        inShipToSection = true;
                        log.info("[P%d] 🔍 检测到 SHIP TO 标签", currentPage + 1);

                    }

                    float paddingX = 2f;
                    float paddingY = 0f;

                    float heightf = first.getHeightDir() * 2.1f;
                    float widthf = (x2 - x1) * 4f;

                    // 然后在创建TextRegion时使用新的widthf和heightf值
                    if (inShipFromSection && (removeType == RemoveType.SHIP_FROM || removeType == RemoveType.BOTH)) {
                        shipFromRegions.add(new TextRegion(currentPage, x1 - paddingX, y - paddingY, x1 + widthf + paddingX, y + heightf + paddingY));
                        inShipFromSection = false;
                    }
                    if (inShipToSection && (removeType == RemoveType.SHIP_TO || removeType == RemoveType.BOTH)) {
                        shipToRegions.add(new TextRegion(currentPage, x1 - paddingX, y - paddingY, x1 + widthf + paddingX, y + heightf + paddingY));
                        inShipToSection = false;
                    }


                    try {
                        super.writeString(string, textPositions);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            };

            stripper.getText(document);

            // 应用遮罩
            applyMasks(document, shipFromRegions, shipToRegions, removeType);


            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            document.save(baos);
            return baos.toByteArray();
        }
    }

    /**
     * 应用遮罩到 PDF 页面
     */
    private static void applyMasks(PDDocument document, List<TextRegion> shipFromRegions,
                                   List<TextRegion> shipToRegions, RemoveType removeType) throws Exception {


        log.info("🎨 开始应用遮罩...");
        for (int i = 0; i < document.getNumberOfPages(); i++) {
            PDPage page = document.getPage(i);
            float pageHeight = page.getMediaBox().getHeight(); // PDF高度，用于翻转Y坐标

            try (PDPageContentStream cs = new PDPageContentStream(document, page, AppendMode.APPEND, true)) {
                cs.setNonStrokingColor(255, 255, 255); // 白色遮罩

                if (removeType == RemoveType.SHIP_FROM || removeType == RemoveType.BOTH) {
                    for (TextRegion r : shipFromRegions) {
                        if (r.pageIndex == i) {
                            float correctedY = pageHeight - r.y2;
                            cs.addRect(r.x1, correctedY, r.x2 - r.x1, r.y2 - r.y1);
                            cs.fill();
                            log.info("[P%d] 🎨 应用 SHIP FROM 遮罩: %.1f×%.1f @(%.1f,%.1f)",
                                    i + 1, r.x2 - r.x1, r.y2 - r.y1, r.x1, correctedY);
                        }
                    }
                }

                if (removeType == RemoveType.SHIP_TO || removeType == RemoveType.BOTH) {
                    for (TextRegion r : shipToRegions) {
                        if (r.pageIndex == i) {
                            float correctedY = pageHeight - r.y2;
                            cs.addRect(r.x1, correctedY, r.x2 - r.x1, r.y2 - r.y1);
                            cs.fill();
                            log.info("[P%d] 🎨 应用 SHIP TO 遮罩: %.1f×%.1f @(%.1f,%.1f)",
                                    i + 1, r.x2 - r.x1, r.y2 - r.y1, r.x1, correctedY);

                        }
                    }
                }
            }
        }
        log.info("✨ 遮罩应用完成！");
    }

    /**
     * 保存文字遮罩区域
     */
    private static class TextRegion {
        int pageIndex;
        float x1, y1, x2, y2;

        public TextRegion(int pageIndex, float x1, float y1, float x2, float y2) {
            this.pageIndex = pageIndex;
            this.x1 = x1;
            this.y1 = y1;
            this.x2 = x2;
            this.y2 = y2;
        }
    }


    public static void main(String[] args) throws Exception {
        String pdfUrl = "https://img.botaili.com/erp/2026/01/28/FBA15LBJHG76_PackageLabel_A4_4.pdf";
        byte[] result = removeShipInfo(pdfUrl, RemoveType.BOTH);

        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSS");
        String timeStamp = LocalDateTime.now().format(formatter);
        String fileName = "redacted_" + timeStamp + ".pdf";

        Files.write(Paths.get(fileName), result);
        log.info("✅ 新 PDF 已生成: " + fileName);
    }
}

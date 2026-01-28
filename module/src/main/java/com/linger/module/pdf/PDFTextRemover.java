package com.linger.module.pdf;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.PDPageContentStream.AppendMode;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

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

            System.out.println("🔍 PDF 总页数: " + document.getNumberOfPages());

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
                    System.out.printf("=== 处理第 %d 页 ===\n", currentPage + 1);
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
                    float height = first.getHeightDir();

                    // 检测标签
// 检测标签
                    if (text.startsWith("SHIP FROM:")) {
                        inShipFromSection = true;
                        System.out.printf("[P%d] 🔍 检测到 SHIP FROM 标签\n", currentPage + 1);
                    } else if (text.startsWith("SHIP TO:")) {
                        inShipToSection = true;
                        System.out.printf("[P%d] 🔍 检测到 SHIP TO 标签\n", currentPage + 1);
                    }

// 只遮罩标签下一行
                    float paddingX = 2f;
                    float paddingY = 2f;

                    if (inShipFromSection && (removeType == RemoveType.SHIP_FROM || removeType == RemoveType.BOTH)) {
                        shipFromRegions.add(new TextRegion(currentPage, x1 - paddingX, y - paddingY,
                                x2 + paddingX, y + height + paddingY));
                        inShipFromSection = false; // 只遮罩一行，立即关闭
                    }

                    if (inShipToSection && (removeType == RemoveType.SHIP_TO || removeType == RemoveType.BOTH)) {
                        shipToRegions.add(new TextRegion(currentPage, x1 - paddingX, y - paddingY,
                                x2 + paddingX, y + height + paddingY));
                        inShipToSection = false; // 只遮罩一行，立即关闭
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

            // 输出 PDF
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

        System.out.println("\n🎨 开始应用遮罩...");

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
                            System.out.printf("[P%d] 🎨 应用 SHIP FROM 遮罩: %.1f×%.1f @(%.1f,%.1f)\n",
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
                            System.out.printf("[P%d] 🎨 应用 SHIP TO 遮罩: %.1f×%.1f @(%.1f,%.1f)\n",
                                    i + 1, r.x2 - r.x1, r.y2 - r.y1, r.x1, correctedY);
                        }
                    }
                }
            }
        }

        System.out.println("✨ 遮罩应用完成！");
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

    /**
     * 测试主方法
     */
    public static void main(String[] args) throws Exception {
        String pdfUrl = "https://img.botaili.com/erp/2026/01/28/FBA15LBJHG76_PackageLabel_A4_4.pdf";
        byte[] result = removeShipInfo(pdfUrl, RemoveType.BOTH);
        java.nio.file.Files.write(java.nio.file.Paths.get("redacted.pdf"), result);
        System.out.println("✅ 新 PDF 已生成: redacted.pdf");
    }
}

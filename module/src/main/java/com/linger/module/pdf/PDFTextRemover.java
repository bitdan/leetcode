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
import java.util.EnumSet;
import java.util.List;
import java.util.Set;

@Slf4j
public class PDFTextRemover {

    public enum RemoveType {
        SHIP_FROM,
        SHIP_TO
    }

    /**
     * 核心方法：移除 SHIP FROM / SHIP TO 地址（支持多个类型）
     */
    public static byte[] removeShipInfo(String pdfUrl, Set<RemoveType> removeTypes) throws Exception {
        try (InputStream in = new URL(pdfUrl).openStream();
             PDDocument document = PDDocument.load(in)) {

            log.info("🔍 正在处理 PDF，共 {} 页", document.getNumberOfPages());

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
                    log.info("[P{}] 🔍 开始解析页面", currentPage + 1);
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

                    // 标签检测
                    if (text.startsWith("SHIP FROM:")) {
                        inShipFromSection = true;
                        log.info("[P{}] 🔍 检测到 SHIP FROM", currentPage + 1);
                    } else if (text.startsWith("SHIP TO:")) {
                        inShipToSection = true;
                        log.info("[P{}] 🔍 检测到 SHIP TO", currentPage + 1);
                    }

                    float paddingX = 2f;
                    float paddingY = 0f;

                    float baseWidth = (x2 - x1);
                    float heightf = first.getHeightDir() * 2.1f;

                    // SHIP FROM：宽度 *3
                    if (inShipFromSection && removeTypes.contains(RemoveType.SHIP_FROM)) {
                        float widthf = baseWidth * 2.5f;

                        shipFromRegions.add(new TextRegion(
                                currentPage,
                                x1 - paddingX,
                                y - paddingY,
                                x1 + widthf + paddingX,
                                y + heightf + paddingY
                        ));
                        inShipFromSection = false;
                    }

                    // SHIP TO：宽度 *4
                    if (inShipToSection && removeTypes.contains(RemoveType.SHIP_TO)) {
                        float widthf = baseWidth * 4f;

                        shipToRegions.add(new TextRegion(
                                currentPage,
                                x1 - paddingX,
                                y - paddingY,
                                x1 + widthf + paddingX,
                                y + heightf + paddingY
                        ));
                        inShipToSection = false;
                    }

                    try {
                        super.writeString(string, textPositions);
                    } catch (Exception e) {
                        log.error("PDF 解析异常", e);
                    }
                }
            };

            stripper.getText(document);

            applyMasks(document, shipFromRegions, shipToRegions, removeTypes);

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            document.save(baos);
            return baos.toByteArray();
        }
    }

    /**
     * 应用遮罩
     */
    private static void applyMasks(PDDocument document,
                                   List<TextRegion> shipFromRegions,
                                   List<TextRegion> shipToRegions,
                                   Set<RemoveType> removeTypes) throws Exception {

        log.info("🎨 开始应用遮罩");

        for (int i = 0; i < document.getNumberOfPages(); i++) {
            PDPage page = document.getPage(i);
            float pageHeight = page.getMediaBox().getHeight();

            try (PDPageContentStream cs =
                         new PDPageContentStream(document, page, AppendMode.APPEND, true)) {

                cs.setNonStrokingColor(255, 255, 255);

                if (removeTypes.contains(RemoveType.SHIP_FROM)) {
                    for (TextRegion r : shipFromRegions) {
                        if (r.pageIndex == i) {
                            float correctedY = pageHeight - r.y2;
                            cs.addRect(r.x1, correctedY, r.x2 - r.x1, r.y2 - r.y1);
                            cs.fill();
                            log.info("[P{}] 🎨 SHIP FROM 遮罩: {}×{}",
                                    i + 1, r.x2 - r.x1, r.y2 - r.y1);
                        }
                    }
                }

                if (removeTypes.contains(RemoveType.SHIP_TO)) {
                    for (TextRegion r : shipToRegions) {
                        if (r.pageIndex == i) {
                            float correctedY = pageHeight - r.y2;
                            cs.addRect(r.x1, correctedY, r.x2 - r.x1, r.y2 - r.y1);
                            cs.fill();
                            log.info("[P{}] 🎨 SHIP TO 遮罩: {}×{}",
                                    i + 1, r.x2 - r.x1, r.y2 - r.y1);
                        }
                    }
                }
            }
        }
        log.info("✨ 遮罩完成");
    }

    /**
     * 遮罩区域模型
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
     * 测试入口
     */
    public static void main(String[] args) throws Exception {
        String pdfUrl = "https://img.botaili.com/erp/2026/01/28/FBA15LBJHG76_PackageLabel_A4_4.pdf";

        Set<RemoveType> removeTypes = EnumSet.of(
                RemoveType.SHIP_TO,
                RemoveType.SHIP_FROM
        );

        byte[] result = removeShipInfo(pdfUrl, removeTypes);
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSS");
        String timeStamp = LocalDateTime.now().format(formatter);
        String fileName = "redacted_" + timeStamp + ".pdf";

        Files.write(Paths.get(fileName), result);

        log.info("✅ 新 PDF 已生成: {}", fileName);
    }
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "리뷰 분석 에이전트",
  description: "『불편한 편의점』 리뷰 데이터를 실시간으로 조회·분석하는 AI 에이전트",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

import { ChatApp } from "@/components/ChatApp";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "法律咨询助手",
  description: "基于大语言模型的法律咨询助手，提供劳动合同、租赁合同等相关法律问题的解答。",
  openGraph: {
    title: "法律咨询助手",
    description: "基于大语言模型的法律咨询助手，提供劳动合同、租赁合同等相关法律问题的解答。",
    url: "https://legal-llm.vercel.app/",
    siteName: "法律咨询助手",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "法律咨询助手",
      },
    ],
    locale: "zh-CN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "法律咨询助手",
    description: "基于大语言模型的法律咨询助手，提供劳动合同、租赁合同等相关法律问题的解答。",
    images: ["/og-image.png"],
  },
};


export default function HomePage() {
  return <ChatApp />;
}

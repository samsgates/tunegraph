import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "TuneGraph Console",
  description: "Govern fine-tuned model behavior"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

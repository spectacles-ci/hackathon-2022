import { useFetcher } from "@remix-run/react";
import { InactiveUserResult, SlowExploresResult } from "../models";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import useSound from "use-sound";
import pop from "../../public/pop.wav";

const transition = {
  type: "spring",
  stiffness: 200,
  mass: 0.2,
  damping: 20,
};

const variants = {
  initial: {
    opacity: 0,
    y: 300,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition,
  },
};

const initialMessages = [
  "welcome to RMLI",
  "let's get to ROASTING 🔥🔥🍗🔥🔥 mwahaha",
  "taking a look (heh) at your Looker instance",
];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function TypingIndicator() {
  return (
    <div className="mt-1 rounded-3xl typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  );
}

export default function Roast() {
  const [messages, setMessages] = useState<string[]>([]);
  const [messageQueue, addToMessageQueue] = useState<string[]>(initialMessages);
  const [isTyping, setTyping] = useState(false);
  const [playSound] = useSound(pop, { volume: 0.5 });

  const inactiveUsers = useFetcher<InactiveUserResult>();
  const slowExplores = useFetcher<SlowExploresResult>();

  useEffect(() => {
    if (messageQueue.length > 0 && !isTyping) {
      setTyping(true);
      const nextMessage = messageQueue.shift();
      const timer = setTimeout(() => {
        setTyping(false);
        playSound();
        setMessages((old) => [...old, nextMessage]);
      }, 2000 + nextMessage.length * 10);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  useEffect(() => {
    if (inactiveUsers.type === "init") {
      inactiveUsers.load("/stats/inactive_users");
    } else if (inactiveUsers.type === "done") {
      addToMessageQueue((old) => [
        ...old,
        `whoa... ${(inactiveUsers.data.pct_inactive * 100).toFixed(
          0
        )}% of your users haven't run a SINGLE query in the last 90 days`,
        "that's... pretty awful",
      ]);
    }
  }, [inactiveUsers.type]);

  useEffect(() => {
    if (slowExplores.type === "init") {
      slowExplores.load("/stats/slow_explores");
    } else if (slowExplores.type === "done") {
      addToMessageQueue((old) => {
        const data = slowExplores.data;
        return [
          ...old,
          "you've got some crazy slow explores 🐢",
          `like "${data.slow_explores[0]["query.model"]}.${data.slow_explores[0]["query.view"]}"`,
          `that thing is a turtle. Takes ${data.slow_explores[0][
            "history.average_runtime"
          ].toFixed(0)} seconds to run on average`,
          `or "${data.slow_explores[1]["query.model"]}.${
            data.slow_explores[1]["query.view"]
          }", which runs for ${data.slow_explores[1][
            "history.average_runtime"
          ].toFixed(0)} seconds on average`,
          "Frank Slootman is worth $1.5 billion dollars. I'd imagine queries from your Looker instance made him at least half of that.",
        ];
      });
    }
  }, [slowExplores.type]);

  return (
    <div className="mx-auto max-w-xl sm:px-6 lg:px-8 py-20 m-auto">
      <AnimatePresence>
        <ol className="flex flex-col items-start max-w-md p-0 list-none">
          {messages.map((text) => (
            <motion.li
              key={text}
              className="bg-gray-200 rounded-xl px-3 py-2.5 leading-6 break-words mb-3"
              initial="initial"
              animate="enter"
              variants={variants}
              layout
            >
              {text}
            </motion.li>
          ))}
        </ol>
        {isTyping && <TypingIndicator />}
      </AnimatePresence>
    </div>
  );
}

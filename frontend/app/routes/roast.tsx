import { useFetcher } from "@remix-run/react";
import {
  InactiveUserResult,
  SlowExploresResult,
  AbandonedDashboardResult,
} from "../models";
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

type Message = {
  text: string;
  pause?: number;
};

const initialMessages: Message[] = [
  { text: "welcome to RMLI" },
  { text: "let's get to ROASTING! 🔥🔥🍗🔥🔥 mwahaha" },
  { text: "taking a look (heh) at your Looker instance", pause: 10000 },
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
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageQueue, addToMessageQueue] = useState(initialMessages);
  const [isTyping, setTyping] = useState(false);
  const [playSound] = useSound(pop, { volume: 0.5 });

  const inactiveUsers = useFetcher<InactiveUserResult>();
  const slowExplores = useFetcher<SlowExploresResult>();
  const abandonedDashboards = useFetcher<AbandonedDashboardResult>();

  useEffect(() => {
    if (messageQueue.length > 0 && !isTyping) {
      setTyping(true);
      const nextMessage = messageQueue.shift();
      const timer = setTimeout(() => {
        setTyping(false);
        playSound();
        setMessages((old) => [...old, nextMessage]);
      }, 2000 + nextMessage.text.length * 10);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  useEffect(() => {
    if (inactiveUsers.type === "init") {
      inactiveUsers.load("/stats/inactive_users");
    } else if (inactiveUsers.type === "done") {
      addToMessageQueue((old) => [
        ...old,
        {
          text: `whoa... ${(inactiveUsers.data.pct_inactive * 100).toFixed(
            0
          )}% of your users haven't run a SINGLE query in the last 90 days`,
          pause: 1000,
        },
        { text: "that's... pretty awful" },
        {
          text: `do you know ${inactiveUsers.data.sample_user_names[0]}? cause I guarantee you ${inactiveUsers.data.sample_user_names[0]} has no idea who you are lol`,
        },
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
          { text: "you've got some crazy slow explores 🐢" },
          {
            text: `like "${data.slow_explores[0]["query.model"]}.${data.slow_explores[0]["query.view"]}"`,
          },
          {
            text: `that thing is a turtle. Takes ${data.slow_explores[0][
              "history.average_runtime"
            ].toFixed(0)} seconds to run on average`,
          },
          {
            text: `or "${data.slow_explores[1]["query.model"]}.${
              data.slow_explores[1]["query.view"]
            }", which runs for ${data.slow_explores[1][
              "history.average_runtime"
            ].toFixed(0)} seconds on average`,
          },
          {
            text: "Frank Slootman is worth $1.5 billion dollars. I'd imagine queries from your Looker instance made him at least half of that.",
            pause: 1000,
          },
        ];
      });
    }
  }, [slowExplores.type]);

  useEffect(() => {
    if (abandonedDashboards.type === "init") {
      abandonedDashboards.load("/stats/abandoned_dashboards");
    } else if (abandonedDashboards.type === "done") {
      addToMessageQueue((old) => {
        const data = abandonedDashboards.data;
        return [
          ...old,
          {
            text: `your Looker instance has ${
              data.count_abandoned / data.pct_abandoned
            } dashboards. wanna guess how many of them were queried over the last 90 days?`,
          },
          { text: "uhh... it's worse than you thought" },
          {
            text: `${data.count_abandoned} of your dashboards just... sat there... unused and unwanted for 90 days and 90 nights`,
          },
          {
            text: `getting about as much attention as you do when you post on LinkedIn`,
            pause: 1000,
          },
        ];
      });
    }
  }, [abandonedDashboards.type]);

  return (
    <div className="mx-auto max-w-xl sm:px-6 lg:px-8 py-20 m-auto">
      <AnimatePresence>
        <ol className="flex flex-col items-start max-w-md p-0 list-none">
          {messages.map(({ text }) => (
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

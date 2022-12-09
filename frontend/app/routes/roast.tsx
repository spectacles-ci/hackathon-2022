import { redirect, LoaderArgs } from "@remix-run/node";
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
import { getSession } from "~/sessions";

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
  { text: "hello hello" },
  { text: "let's get to ROASTING! 🔥🔥🍗🔥🔥 mwahaha" },
  {
    text: "running some API and system activity queries to take a look (heh) at your Looker instance",
  },
];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function TypingIndicator() {
  return (
    <div className="mt-1 rounded-3xl typing-indicator flex self-start">
      <span></span>
      <span></span>
      <span></span>
    </div>
  );
}

export async function loader({ request }: LoaderArgs) {
  const session = await getSession(request.headers.get("Cookie"));
  if (!session.has("credentialId")) {
    return redirect("/auth");
  }
  return null;
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
    scrollToBottom();
    if (messageQueue.length > 0 && !isTyping) {
      setTyping(true);
      const nextMessage = messageQueue.shift();
      const timer = setTimeout(() => {
        setTyping(false);
        playSound();
        setMessages((old) => [...old, nextMessage]);
      }, 2000 + nextMessage.text.length * 20);
      return () => clearTimeout(timer);
    }
  }, [messages]);

  function scrollToBottom() {
    // Get the total height of the page
    var pageHeight = document.body.scrollHeight;

    // Scroll to the bottom of the page
    window.scrollTo(0, pageHeight);
  }

  useEffect(() => {
    if (inactiveUsers.type === "init") {
      inactiveUsers.load("/stats/inactive_users");
    } else if (inactiveUsers.type === "done") {
      addToMessageQueue((old) => {
        const data = inactiveUsers.data;
        let pre_response = [
          { text: "🤝" },
          {
            text: "let's have a look at whether you're doing a good job at getting people to actually use Looker. ya know, self-service analytics and all that.",
          },
          { text: "just pulling the information from your instance now..." },
        ];
        if (data.grade === "bad") {
          var inactive_user_responses = [
            {
              text: `whoa... ${(data.pct_inactive * 100).toFixed(
                0
              )}% of your users haven't run a SINGLE query in the last 90 days`,
            },
            { text: "that's... pretty awful" },
            {
              text: `do you know ${data.sample_user_names[0]}? cause I guarantee you ${inactiveUsers.data.sample_user_names[0]} has no idea who you are lol`,
            },
            {
              text: "the system activity explore... it's a thing. you should use it",
            },
          ];
          if (data.sample_user_names.length > 3) {
            inactive_user_responses.push({
              text: `maybe drop a message to ${data.sample_user_names[1]} and ${data.sample_user_names[2]} too. They are some of your oldest Looker users. For your sake, I hope they don't work at the company any more...`,
            });
          }
        } else if (data.grade === "ok") {
          var inactive_user_responses = [
            { text: "like, this isn't terrible... it's not great though." },
            {
              text: `${(data.pct_inactive * 100).toFixed(
                0
              )}% of your users haven't run a single query in last little bit`,
            },
            { text: "and by last little bit, I mean 90 days. 90 DAYS?!" },
            {
              text: `maybe go check in with ${data.sample_user_names[0]}. do they know you've wasted a Looker license on them?`,
            },
            {
              text: "you might also want to think about using the system activity explore every once in a while to see if you've got any users who are just... not using Looker",
            },
          ];
        } else {
          var inactive_user_responses = [
            {
              text: "hey. would you look at that. maybe you're not totally incompetent.",
            },
            {
              text: `you've got a few users who haven't run any queries in the last 90 days, but it seems it's only ${(
                data.pct_inactive * 100
              ).toFixed(0)}% of them`,
            },
            {
              text: `that said, ${data.sample_user_names[0]} seems like they are totally unaware of Looker. maybe drop them a line`,
            },
          ];
        }
        return [...old, ...pre_response, ...inactive_user_responses];
      });
    }
  }, [inactiveUsers.type]);

  useEffect(() => {
    if (slowExplores.type === "init") {
      slowExplores.load("/stats/slow_explores");
    } else if (slowExplores.type === "done") {
      addToMessageQueue((old) => {
        const data = slowExplores.data;
        let pre_response = [
          { text: "🏎" },
          {
            text: "you know what they say: a fast Looker instance is a Looker instance people will actually bother to use",
          },
          {
            text: "or something like that, I'm pretty sure. Not a big fan of proverbs",
          },
          { text: "anyway, let's see how you're doing on the speed front" },
        ];
        if (data.grade === "bad") {
          var slow_explores_responses = [
            {
              text: "😩 biiiiig ooof. how do people at your company even use this thing?",
            },
            {
              text: `your slowest explore, "${
                data.slow_explores[0]["query.model"]
              }.${data.slow_explores[0]["query.view"]}", 
              takes ${data.slow_explores[0]["history.average_runtime"].toFixed(
                0
              )} seconds to run on average`,
            },
            { text: "that. is. brutal." },
            {
              text: `and that's the AVERAGE. the mean. one time, it took ${data.slow_explores[0][
                "history.max_runtime"
              ].toFixed(0)} seconds to run.`,
            },
            {
              text: "heard the person who ran that query quit the company the next day. I'm not sure if that's true, but I wouldn't be surprised.",
            },
            {
              text: "are your colleagues well caffeinated? They definitely have enough time to make plenty of coffee while they wait for these painfully slow explores to run.",
            },
            {
              text: `"${data.slow_explores[1]["query.model"]}.${
                data.slow_explores[1]["query.view"]
              }" is another one. it's slightly better, but it still takes ${data.slow_explores[1][
                "history.average_runtime"
              ].toFixed(0)} seconds on average`,
            },
            {
              text: "i'm not sure what to say. I'm just going to leave this here for you to think about",
            },
            {
              text: "maybe have a look at the history explore in the system activity model. It'll help you find more of these so you can start fixing them.",
            },
          ];
        } else if (data.grade === "ok") {
          var slow_explores_responses = [
            { text: "okay... do you want the good or the bad first?" },
            {
              text: "the good? I've seen worse. Not much worse, but definitely worse.",
            },
            {
              text: "that's the end of the good news. The bad news is that I've watched soccer games that finish faster than your slowest explore.",
            },
            {
              text: `"${data.slow_explores[0]["query.model"]}.${
                data.slow_explores[0]["query.view"]
              }" is the worst offender. It takes ${data.slow_explores[0][
                "history.average_runtime"
              ].toFixed(0)} to complete a query on average.`,
            },
            {
              text: `that's the average runtime as well. at its worst it occasionally runs for up to ${data.slow_explores[0][
                "history.max_runtime"
              ].toFixed(0)} seconds.`,
            },
            {
              text: `that's not the only bad explore though. "${
                data.slow_explores[1]["query.model"]
              }.${
                data.slow_explores[1]["query.view"]
              }" also runs at a glacial pace. 
            It takes ${data.slow_explores[1]["history.average_runtime"].toFixed(
              0
            )} seconds to run on average.`,
            },
            {
              text: "maybe have a look at the history explore in the system activity model. It'll help you find more of these so you can start fixing them.",
            },
          ];
        } else {
          var slow_explores_responses = [
            { text: "not bad... not bad at all." },
            { text: `your slowest explore isn't actually that slow.` },
            {
              text: `"${data.slow_explores[0]["query.model"]}.${
                data.slow_explores[0]["query.view"]
              }" takes ${data.slow_explores[0][
                "history.average_runtime"
              ].toFixed(0)} seconds to run on average.`,
            },
            {
              text: `it does occasionally take up to ${data.slow_explores[0][
                "history.max_runtime"
              ].toFixed(0)} seconds to run, but no one is perfect I guess.`,
            },
            {
              text: "i'm just going to assume you're dealing with Very Small Data™️ It's easy to make explores run quickly when there's only a few rows of data in there.",
            },
            {
              text: `just so you're aware, the next slowest explore is "${
                data.slow_explores[1]["query.model"]
              }.${
                data.slow_explores[1]["query.view"]
              }". It takes ${data.slow_explores[1][
                "history.average_runtime"
              ].toFixed(0)} seconds to run on average.`,
            },
            {
              text: "you can find some big public datasets online if you want to see what it's like to run Looker on real data like other companies.",
            },
          ];
        }
        return [...old, ...pre_response, ...slow_explores_responses];
      });
    }
  }, [slowExplores.type]);

  useEffect(() => {
    if (abandonedDashboards.type === "init") {
      abandonedDashboards.load("/stats/abandoned_dashboards");
    } else if (abandonedDashboards.type === "done") {
      addToMessageQueue((old) => {
        const data = abandonedDashboards.data;
        let pre_response = [
          { text: "👀" },
          { text: "not gonna lie, I'm a little nervous about this next one" },
          {
            text: "let's have a look at how much usage all those precious dashboards you built are getting...",
          },
        ];
        if (data.grade === "bad") {
          var abandoned_dashboard_responses = [
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
            },
            // https://help.looker.com/hc/en-us/articles/4419767469587-Deleted-and-unused-content-for-admins
            {
              text: "maybe have a look at the unused content report in Looker and get some of those cleaned up. You'll thank me.",
              pause: 1000,
            },
          ];
        } else if (data.grade === "ok") {
          var abandoned_dashboard_responses = [
            { text: "do you know what? This could have been a lot worse" },
            {
              text: `you've got ${
                data.count_abandoned
              } abandoned dashboards, which is ${(
                data.pct_abandoned * 100
              ).toPrecision(2)}% of your total dashboards`,
            },
            {
              text: `that's ${data.count_abandoned} of your dashboards that haven't had a SINGLE query in the last 90 days...`,
            },
            // https://help.looker.com/hc/en-us/articles/4419767469587-Deleted-and-unused-content-for-admins
            {
              text: "maybe have a look at the unused content report in Looker and get some of those cleaned up. You'll thank me.",
              pause: 1000,
            },
          ];
        } else {
          var abandoned_dashboard_responses = [
            {
              text: "huh. This is actually pretty good. Did a consultant set this up for you? Is this a brand new Looker instance?",
            },
            {
              text: `you've got ${
                data.count_abandoned / data.pct_abandoned
              } dashboards in total, and only ${
                data.count_abandoned
              } of them haven't been used in the last 90 days`,
              pause: 1000,
            },
            { text: "that's better than most Looker instances I've seen 👏" },
            { text: "PROUD 👏 OF 👏 YOU 👏" },
          ];
        }
        return [...old, ...pre_response, ...abandoned_dashboard_responses];
      });
    }
  }, [abandonedDashboards.type]);

  return (
    <>
      <div className="flex flex-col h-screen mx-auto max-w-xl sm:px-6 lg:px-8 py-20 m-auto">
        <div className="flex flex-col grow">
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
        <p className="mt-8 pb-8 text-center text-sm text-gray-400">
          Built with ❤️ (and snark) by the team at{" "}
          <a className="underline" href="https://spectacles.dev">
            Spectacles
          </a>
        </p>
      </div>
    </>
  );
}

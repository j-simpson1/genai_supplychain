import Header from "../components/Header";
import { useState, useEffect } from "react";
import {
  Chat,
  Channel,
  ChannelList,
  Window,
  ChannelHeader,
  MessageList,
  MessageInput,
  Thread,
} from "stream-chat-react";
import { StreamChat } from "stream-chat";
import "stream-chat-react/dist/css/v2/index.css";

interface TokenRequest {
  userId: string;
}

const apiKey = import.meta.env.VITE_REACT_APP_STREAM_API_KEY;
console.log("API Key available:", !!apiKey);
const userId = "js-user";
const filters = { members: { $in: [userId] }, type: "messaging" };
const options = { presence: true, state: true };
const sort = { last_message_at: -1 };

const ChatPage = () => {
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initChat = async () => {
      try {
        // Call your FastAPI endpoint to get the token
        const response = await fetch('http://127.0.0.1:8000/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ userId }),
        });

        if (!response.ok) {
          throw new Error('Failed to fetch token');
        }

        const { token } = await response.json();

        // Initialize the Stream chat client
        const chatClient = StreamChat.getInstance(apiKey);
        await chatClient.connectUser(
          { id: userId, name: 'James Simpson' },
          token
        );

        setClient(chatClient);
      } catch (err) {
        console.error("Error initializing chat:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    initChat();

    // Cleanup
    return () => {
      if (client) client.disconnectUser();
    };
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!client) return <div>Could not initialize chat client</div>;

  return (
    <>
      <Header />
      <Chat client={client}>
        <ChannelList sort={sort} filters={filters} options={options} />
        <Channel>
          <Window>
            <ChannelHeader />
            <MessageList />
            <MessageInput />
          </Window>
          <Thread />
        </Channel>
      </Chat>
    </>
  );
};

export default ChatPage;
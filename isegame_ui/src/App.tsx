import { useEffect, useState } from "react"
import { GameState, Question, SocketClient, User } from "./client"
import {
  Heading,
  Box,
  Button,
  ChakraProvider,
  Flex,
  extendTheme,
  CardHeader,
  Card,
  Grid,
  GridItem,
  Tr,
  Table,
  Thead,
  Th,
  Tbody,
  Td,
  Spacer,
  CardFooter,
  ThemeConfig,
} from "@chakra-ui/react"
import { Input, Text } from '@chakra-ui/react'
import { VStack } from '@chakra-ui/react'
import { SimpleGrid } from '@chakra-ui/react'
import { v4 as uuidv4 } from 'uuid'
import { useToast } from '@chakra-ui/react'

const pieceMap = [
  '♙', '♖', '♘', '♗', '♔', '♕',
]

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
}

const theme = extendTheme({ config })

function App() {
  const [socket, setSocket] = useState<SocketClient | undefined>(undefined)

  /**
   * The current user
   */
  const [user, setUser] = useState<User | undefined>(undefined)

  /**
   * The list of clients
   */
  const [clients, setClients] = useState<User[]>([])

  /**
   * The current game state
   */
  const [state, setState] = useState<GameState | undefined>(undefined)
  const [question, setQuestion] = useState<Question | undefined>(undefined)
  const [correct, setCorrect] = useState<boolean | null>(null)
  const [timer, setTimer] = useState(0)

  const toast = useToast()

  useEffect(() => {
    const socketUrl = import.meta.env.MODE === "development"
      ? "ws://localhost:3001/ws"
      : `ws://${window.location.host}/ws`

    SocketClient.createClient(socketUrl).then(socket => {
      setSocket(socket)

      socket.on("clients", ({ clients }) => setClients(clients))
      socket.on("state", ({ state }) => setState(state))
      socket.on("identity", ({ client }) => setUser(client))

      socket.on("stop", () => setState(undefined))
      socket.on("question", (question) => setQuestion(question.question))
      socket.on("answer", ({ correct, question }) => {
        setCorrect(correct)

        setTimeout(() => {
          setCorrect(null)
          setQuestion(question)
        }, correct ? 1000 : 3000)
      })

      socket.on("timer", ({ time }) => setTimer(time))

      socket.send({ action: "clients" })
    })
  }, [])

  useEffect(() => {
    if (socket) {
      socket.on("error", ({ message }) => {
        toast({
          title: message,
          status: 'error',
          duration: 9000,
          isClosable: true,
        })
      })
    }
  }, [toast, socket])

  return (
    <ChakraProvider theme={theme}>
      {user && <Bar user={user} state={state} timer={timer} />}
      <Box minH="100vh" h="100%">
        <Flex justifyContent="center" w="100%">
          {socket &&
            (
              user ? <Box mt={"30px"}>
                {state ? <>
                  {state.status == "round"
                    ? <QuestionDisplay question={question!} socket={socket} correct={correct} />
                    : <Leaderboard users={clients} state={state} />}
                </> : <CardList users={clients} />}
              </Box> : <JoinScreen socket={socket} clients={clients} />
            )
          }
        </Flex>
      </Box>
    </ChakraProvider >
  )
}

const Bar = ({ user, state, timer }: { user: User, state?: GameState, timer: number }) => {
  return (
    <>
      <Box bg="gray.900" px={4} position="relative">
        <Flex h={16} alignItems='center'>
          <Box fontSize="2xl"><b>{pieceMap[user.piece]} {user.name}</b></Box>
          <Spacer />
          {(state !== undefined && state.scores[user.id] !== undefined)  && <Box>{state.scores[user.id]}</Box>}
          {timer &&
            <Box
              fontSize="xl"
              position="absolute"
              left="50%"
              transform="translateX(-50%)"
            >
              {timer} seconds left!
            </Box>
          }
        </Flex>
      </Box>
    </>
  )
}

const CardList = ({ users }: { users: User[] }) => {
  return (
    <VStack align="center" spacing={5}>
      <Heading size="xl">Players</Heading>
      <Flex flexWrap="wrap" justifyContent="center" gap="15px">
        {users.map((user) => (
          <Box key={user.id} display="flex" justifyContent="center">
            <PlayerCard user={user} />
          </Box>
        ))}
      </Flex>
    </VStack >
  )
}

const QuestionDisplay = ({
  question,
  socket,
  correct
}: {
  question: Question,
  socket: SocketClient,
  correct: boolean | null
}) => {
  return (
    <Flex direction="column" justify="center" align="center" minHeight="100vh" p={5}>
      <Box w="100%" minH="50vh">
        <Heading size="2xl" textAlign="center" my={5}>{question.question}</Heading>
      </Box>
      <Box w="100%" minH="50vh">
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={5}>
          {question.options.map((option, idx) => (
            <Button
              isDisabled={correct !== null}
              bg={correct === true ? "green" : correct === false ? "red" : undefined}
              color={correct !== null ? "white" : undefined}
              _hover={{ bg: correct === true ? "green" : correct === false ? "red" : undefined }}
              key={uuidv4()}
              fontSize="2xl"
              height="100%"
              p={8}
              onClick={() => socket.send({ action: "answer", answer: idx })}
            >
              {option}
            </Button>
          ))}
        </SimpleGrid>
      </Box>
    </Flex>
  )
}

const Leaderboard = ({ users, state }: { users: User[], state: GameState }) => {
  const sorted = users.sort((a, b) => state.scores[b.id] - state.scores[a.id])

  return (
    <VStack>
      <Heading size="xl">Leaderboard</Heading>
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Name</Th>
            <Th>Score</Th>
            <Th>Move Spaces</Th>
          </Tr>
        </Thead>
        <Tbody>
          {sorted.map((user) => (
            <Tr key={user.id}>
              <Td>{pieceMap[user.piece]} {user.name}</Td>
              <Td>{state.scores[user.id]}</Td>
              <Td>{state.move_spaces?.[user.id]}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </VStack>
  )
}

const PlayerCard = ({ user }: { user: User }) => {
  return (
    <Card>
      <CardHeader>
        <Heading size='lg'>{pieceMap[user.piece]} {user.name}</Heading>
      </CardHeader>
      <CardFooter>
        <Text pt='2' fontSize='xs'>
          {user.id}
        </Text>
      </CardFooter>
    </Card>
  )
}

const JoinScreen: React.FC<{ socket: SocketClient, clients: User[] }> = ({ socket, clients }) => {
  const [name, setName] = useState("")
  const [piece, setPiece] = useState(0)

  return (
    <VStack
      h="100vh"
      justifyContent="center"
      w="500px"
    >
      <Heading>Join Game</Heading>
      <Input value={name} placeholder='Your name' onChange={(e) => setName(e.target.value)} />
      <Grid templateColumns='repeat(6, 1fr)' gap={4}>
        {pieceMap.map((option, index) => (
          <GridItem key={index}>
            <Box w="100%" h="10">
              <Button fontSize="4xl"
                variant={piece === index ? "solid" : "outline"}
                isDisabled={clients.find(c => c.piece === index) !== undefined}
                onClick={() => setPiece(pieceMap.indexOf(option))}>
                {option}
              </Button>
            </Box>
          </GridItem>
        ))}
      </Grid>
      <Button w="100%" onClick={() => {
        socket?.send({ action: "join", name, piece })
      }}>
        Join
      </Button>
    </VStack >
  )
}

export default App

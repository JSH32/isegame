export interface User {
  id: string
  name: string,
  piece: number
}

export interface Question {
  question: string
  options: number[]
}

export interface GameState {
  scores: { [id: string]: number }
  status: "round" | "paused"
}

type SendSocketMessage =
  { action: 'join', name: string, piece: number } |
  { action: 'clients' } |
  { action: 'answer', answer: number } // Answer here is the index of the option

/**
 * All messages that can be sent from the Socket.
 */
type SocketMessage =
  { action: 'clients', clients: User[] } |
  { action: 'state', state: GameState } |
  { action: 'stop' } |
  // The first state call starts the game.
  { action: 'state', state: GameState } |
  { action: 'question', question: Question } |
  { action: 'identity', client: User } |
  { action: 'answer', correct: boolean, question: Question } |
  { action: 'timer', time: number } |
  { action: 'error', message: string }

/**
 * The client that connects to the server
 */
export class SocketClient {
  private socket: WebSocket
  private callbacks: { [type: string]: ((message: SocketMessage) => void)[] } = {}

  private constructor(uri: string) {
    this.socket = new WebSocket(uri)
    this.socket.addEventListener("message", (event) => {
      this.onMessage(event.data)
    })
  }

  public static async createClient(uri: string): Promise<SocketClient> {
    const client = new SocketClient(uri)

    return new Promise(resolve => {
      client.socket.onopen = () => {
        resolve(client)
      }
    })
  }

  /**
   * Wait for the connection to be open
   * @returns 
   */
  private waitForOpenConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      const maxNumberOfAttempts = 10
      const intervalTime = 200 //ms

      let currentAttempt = 0
      const interval = setInterval(() => {
        if (currentAttempt > maxNumberOfAttempts - 1) {
          clearInterval(interval)
          reject(new Error('Maximum number of attempts exceeded'))
        } else if (this.socket.readyState === this.socket.OPEN) {
          clearInterval(interval)
          resolve()
        }
        currentAttempt++
      }, intervalTime)
    })
  }

  private onMessage(stringMessage: string) {
    const message: SocketMessage = JSON.parse(stringMessage)

    if (this.callbacks[message.action]) {
      this.callbacks[message.action].forEach(c => c(message))
    }
  }

  /**
   * Make a method called `on` which accepts a callback of the proper {@link SocketMessage} type with the type provided.
   * @param callback The callback function to be executed when a message of the proper type is received.
   */
  public on<T extends SocketMessage['action']>(type: T, callback: (message: Extract<SocketMessage, { action: T }>) => void) {
    if (!this.callbacks[type]) {
      this.callbacks[type] = []
    }

    this.callbacks[type].push(callback as (message: SocketMessage) => void)
  }

  /**
   * Send a message to the server
   * @param message The message to send
   */
  public async send<T extends SendSocketMessage['action']>(message: Extract<SendSocketMessage, { action: T }>) {
    if (this.socket.readyState !== this.socket.OPEN) {
      try {
        await this.waitForOpenConnection()
        this.socket.send(JSON.stringify(message))
      } catch (err) { console.error(err) }
    } else {
      this.socket.send(JSON.stringify(message))
    }
  }
}
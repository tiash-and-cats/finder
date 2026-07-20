import { NextResponse } from 'next/server'

export function proxy(request) {
  if (process.env.LOGGING_LEVEL != "DEBUG") {
    return NextResponse.next()
  }
  
  console.log(`DEBUG: ${request.method} ${request.nextUrl}`)

  return NextResponse.next()
}
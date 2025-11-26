# 🎨 프론트엔드 상세 가이드

> Next.js 16 App Router + React 19 + TypeScript 심층 분석

## 📋 목차

1. [App Router 이해하기](#app-router-이해하기)
2. [컴포넌트 패턴](#컴포넌트-패턴)
3. [상태 관리](#상태-관리)
4. [API 통신 패턴](#api-통신-패턴)
5. [새 페이지 추가하기](#새-페이지-추가하기)
6. [스타일링](#스타일링)

---

## App Router 이해하기

Next.js 16의 App Router는 파일 시스템 기반 라우팅을 사용합니다.

### 라우팅 규칙

```
app/                          → localhost:3000/
├── page.tsx                  → /
├── layout.tsx                → 모든 페이지의 공통 레이아웃
│
├── login/
│   └── page.tsx              → /login
│
├── financial-statements/
│   ├── page.tsx              → /financial-statements (있으면)
│   ├── list/
│   │   └── page.tsx          → /financial-statements/list
│   ├── create/
│   │   └── page.tsx          → /financial-statements/create
│   └── [id]/                 → 동적 라우트
│       ├── page.tsx          → /financial-statements/123
│       └── upload/
│           └── page.tsx      → /financial-statements/123/upload
```

### 특수 파일들

| 파일 | 용도 |
|------|------|
| `page.tsx` | 해당 라우트의 UI |
| `layout.tsx` | 하위 라우트들의 공통 레이아웃 |
| `loading.tsx` | 로딩 UI (Suspense 기반) |
| `error.tsx` | 에러 바운더리 |
| `not-found.tsx` | 404 페이지 |

### 루트 레이아웃

```tsx
// app/layout.tsx
import './globals.css';
import { AuthProvider } from '../contexts/AuthContext';
import Navbar from '../components/Navbar';

export const metadata = {
    title: 'SamSamOO AI Platform',
    description: 'AI 기반 재무제표 분석 플랫폼'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="ko">
            <body>
                {/* AuthProvider로 전체 앱을 감싸서 인증 상태 공유 */}
                <AuthProvider>
                    <Navbar />
                    <main>{children}</main>
                </AuthProvider>
            </body>
        </html>
    );
}
```

---

## 컴포넌트 패턴

### 서버 컴포넌트 vs 클라이언트 컴포넌트

Next.js App Router에서는 기본적으로 **서버 컴포넌트**입니다.

```tsx
// 서버 컴포넌트 (기본) - 브라우저 API 사용 불가
// 데이터 페칭, SEO에 유리
export default async function ServerComponent() {
    // 서버에서 직접 데이터 페칭 가능
    const data = await fetch('https://api.example.com/data');
    
    return <div>{data}</div>;
}
```

```tsx
// 클라이언트 컴포넌트 - 브라우저 API 사용 가능
// useState, useEffect 등 React 훅 사용 가능
"use client";  // ⚠️ 파일 최상단에 반드시 명시

import { useState, useEffect } from 'react';

export default function ClientComponent() {
    const [count, setCount] = useState(0);
    
    useEffect(() => {
        // 브라우저에서만 실행
        console.log('클라이언트에서 마운트됨');
    }, []);
    
    return (
        <button onClick={() => setCount(c => c + 1)}>
            Count: {count}
        </button>
    );
}
```

### 언제 "use client" 를 사용할까?

| 상황 | 서버/클라이언트 |
|------|----------------|
| useState, useEffect 등 훅 사용 | 클라이언트 |
| onClick 등 이벤트 핸들러 | 클라이언트 |
| 브라우저 API (localStorage 등) | 클라이언트 |
| 정적 컨텐츠 렌더링 | 서버 |
| 서버에서 데이터 페칭 | 서버 |
| SEO가 중요한 페이지 | 서버 |

### 컴포넌트 구성 예시

```tsx
// app/financial-statements/list/page.tsx
"use client";

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface Statement {
    id: number;
    company_name: string;
    fiscal_year: number;
    created_at: string;
}

export default function FinancialStatementListPage() {
    const { isLoggedIn } = useAuth();
    const [statements, setStatements] = useState<Statement[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!isLoggedIn) return;
        
        fetchStatements();
    }, [isLoggedIn]);

    const fetchStatements = async () => {
        try {
            setLoading(true);
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/financial-statements/list`,
                { credentials: 'include' }  // ⚠️ 필수!
            );
            
            if (!response.ok) {
                throw new Error('재무제표 목록을 불러오는데 실패했습니다');
            }
            
            const data = await response.json();
            setStatements(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : '알 수 없는 오류');
        } finally {
            setLoading(false);
        }
    };

    // 조건부 렌더링
    if (!isLoggedIn) {
        return <div className="p-6">로그인이 필요합니다</div>;
    }

    if (loading) {
        return <div className="p-6">로딩 중...</div>;
    }

    if (error) {
        return <div className="p-6 text-red-500">오류: {error}</div>;
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">재무제표 목록</h1>
            
            {statements.length === 0 ? (
                <p>등록된 재무제표가 없습니다.</p>
            ) : (
                <ul className="space-y-2">
                    {statements.map((stmt) => (
                        <li key={stmt.id} className="p-4 border rounded">
                            <a href={`/financial-statements/${stmt.id}`}>
                                {stmt.company_name} - {stmt.fiscal_year}년
                            </a>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
```

---

## 상태 관리

### Context API 패턴

이 프로젝트에서는 React Context API를 사용합니다.

```tsx
// contexts/AuthContext.tsx
"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// 1. Context 타입 정의
interface AuthContextType {
    isLoggedIn: boolean;
    user: User | null;
    refresh: () => void;
    logout: () => void;
}

interface User {
    id: number;
    email: string;
    name: string;
}

// 2. Context 생성 (기본값 설정)
const AuthContext = createContext<AuthContextType>({
    isLoggedIn: false,
    user: null,
    refresh: () => {},
    logout: () => {},
});

// 3. Provider 컴포넌트
export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState<User | null>(null);

    const refresh = async () => {
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/authentication/status`,
                { credentials: 'include' }
            );
            const data = await response.json();
            
            setIsLoggedIn(data.logged_in);
            setUser(data.user || null);
        } catch {
            setIsLoggedIn(false);
            setUser(null);
        }
    };

    const logout = async () => {
        await fetch(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/authentication/logout`,
            { method: 'POST', credentials: 'include' }
        );
        setIsLoggedIn(false);
        setUser(null);
    };

    // 앱 시작 시 인증 상태 확인
    useEffect(() => {
        refresh();
    }, []);

    return (
        <AuthContext.Provider value={{ isLoggedIn, user, refresh, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

// 4. 커스텀 훅 (편리한 사용을 위해)
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};
```

### 컴포넌트에서 사용

```tsx
"use client";

import { useAuth } from '@/contexts/AuthContext';

export default function ProfilePage() {
    const { isLoggedIn, user, logout } = useAuth();

    if (!isLoggedIn) {
        return <div>로그인이 필요합니다</div>;
    }

    return (
        <div>
            <h1>환영합니다, {user?.name}님!</h1>
            <p>이메일: {user?.email}</p>
            <button onClick={logout}>로그아웃</button>
        </div>
    );
}
```

---

## API 통신 패턴

### 기본 패턴 (fetch 사용)

```tsx
// ⚠️ 중요: credentials: 'include' 항상 포함!
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

// GET 요청
async function fetchData(endpoint: string) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: 'include',  // 세션 쿠키 전송
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

// POST 요청
async function postData(endpoint: string, data: object) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

// 파일 업로드
async function uploadFile(endpoint: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        credentials: 'include',
        // ⚠️ Content-Type 헤더를 설정하지 않음 - FormData가 자동 설정
        body: formData,
    });
    
    if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
    }
    
    return response.json();
}
```

### 커스텀 훅으로 추상화

```tsx
// hooks/useApi.ts
"use client";

import { useState, useCallback } from 'react';

interface UseApiOptions {
    onSuccess?: (data: any) => void;
    onError?: (error: Error) => void;
}

export function useApi<T>(options: UseApiOptions = {}) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const execute = useCallback(async (
        endpoint: string,
        fetchOptions: RequestInit = {}
    ) => {
        try {
            setLoading(true);
            setError(null);
            
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}${endpoint}`,
                {
                    credentials: 'include',
                    ...fetchOptions,
                }
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            setData(result);
            options.onSuccess?.(result);
            return result;
            
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Unknown error');
            setError(error);
            options.onError?.(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [options]);

    return { data, loading, error, execute };
}
```

```tsx
// 사용 예시
"use client";

import { useApi } from '@/hooks/useApi';

export default function MyComponent() {
    const { data, loading, error, execute } = useApi<Statement[]>();

    useEffect(() => {
        execute('/financial-statements/list');
    }, []);

    // ...
}
```

---

## 새 페이지 추가하기

### 예시: 알림 페이지 추가

#### Step 1: 페이지 파일 생성

```tsx
// app/notifications/page.tsx
"use client";

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface Notification {
    id: number;
    title: string;
    message: string;
    is_read: boolean;
    created_at: string;
}

export default function NotificationsPage() {
    const { isLoggedIn } = useAuth();
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isLoggedIn) return;
        fetchNotifications();
    }, [isLoggedIn]);

    const fetchNotifications = async () => {
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/notifications/list`,
                { credentials: 'include' }
            );
            const data = await response.json();
            setNotifications(data);
        } catch (error) {
            console.error('알림 로딩 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    const markAsRead = async (id: number) => {
        try {
            await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/notifications/${id}/read`,
                { method: 'POST', credentials: 'include' }
            );
            // 로컬 상태 업데이트
            setNotifications(prev => 
                prev.map(n => n.id === id ? { ...n, is_read: true } : n)
            );
        } catch (error) {
            console.error('읽음 처리 실패:', error);
        }
    };

    if (!isLoggedIn) {
        return (
            <div className="p-6 text-center">
                <p>로그인이 필요합니다</p>
            </div>
        );
    }

    if (loading) {
        return <div className="p-6">로딩 중...</div>;
    }

    return (
        <div className="p-6 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">알림</h1>
            
            {notifications.length === 0 ? (
                <p className="text-gray-500">알림이 없습니다</p>
            ) : (
                <ul className="space-y-3">
                    {notifications.map((notification) => (
                        <li 
                            key={notification.id}
                            className={`p-4 rounded-lg border ${
                                notification.is_read 
                                    ? 'bg-gray-50 border-gray-200' 
                                    : 'bg-blue-50 border-blue-200'
                            }`}
                        >
                            <div className="flex justify-between items-start">
                                <div>
                                    <h3 className="font-semibold">
                                        {notification.title}
                                    </h3>
                                    <p className="text-gray-600 mt-1">
                                        {notification.message}
                                    </p>
                                    <span className="text-xs text-gray-400 mt-2 block">
                                        {new Date(notification.created_at).toLocaleString('ko-KR')}
                                    </span>
                                </div>
                                
                                {!notification.is_read && (
                                    <button
                                        onClick={() => markAsRead(notification.id)}
                                        className="text-sm text-blue-600 hover:underline"
                                    >
                                        읽음
                                    </button>
                                )}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
```

#### Step 2: 네비게이션에 링크 추가

```tsx
// components/Navbar.tsx
import Link from 'next/link';

// 기존 네비게이션 항목에 알림 링크 추가
<Link href="/notifications" className="nav-link">
    알림
</Link>
```

#### Step 3: 타입 정의 추가 (선택)

```tsx
// types/notification.ts
export interface Notification {
    id: number;
    notification_type: string;
    title: string;
    message: string;
    is_read: boolean;
    created_at: string;
}

export type NotificationType = 'analysis_complete' | 'system_alert';
```

---

## 스타일링

### Tailwind CSS 사용

이 프로젝트는 Tailwind CSS 4를 사용합니다.

```tsx
// 기본 사용
<div className="p-6 bg-white rounded-lg shadow-md">
    <h1 className="text-2xl font-bold text-gray-800 mb-4">
        제목
    </h1>
    <p className="text-gray-600">
        내용
    </p>
</div>
```

### 자주 사용하는 유틸리티 클래스

```tsx
// 레이아웃
<div className="flex items-center justify-between">     {/* 플렉스박스 */}
<div className="grid grid-cols-3 gap-4">               {/* 그리드 */}
<div className="max-w-2xl mx-auto">                    {/* 중앙 정렬 */}

// 여백
<div className="p-4">     {/* padding 전체 */}
<div className="px-4">    {/* padding 좌우 */}
<div className="py-4">    {/* padding 상하 */}
<div className="m-4">     {/* margin 전체 */}
<div className="mb-4">    {/* margin-bottom */}

// 텍스트
<p className="text-sm text-gray-500">      {/* 작은 회색 텍스트 */}
<h1 className="text-2xl font-bold">        {/* 큰 굵은 텍스트 */}
<span className="text-red-500">            {/* 빨간 텍스트 */}

// 버튼 스타일
<button className="
    px-4 py-2 
    bg-blue-600 text-white 
    rounded-lg 
    hover:bg-blue-700 
    transition-colors
">
    클릭
</button>

// 카드 스타일
<div className="
    p-6 
    bg-white 
    rounded-lg 
    border border-gray-200 
    shadow-sm 
    hover:shadow-md 
    transition-shadow
">
    카드 내용
</div>

// 조건부 스타일
<div className={`
    p-4 rounded-lg 
    ${isActive ? 'bg-blue-100 border-blue-500' : 'bg-gray-100 border-gray-300'}
`}>
```

### 반응형 디자인

```tsx
// 반응형 그리드
<div className="
    grid 
    grid-cols-1       /* 모바일: 1열 */
    md:grid-cols-2    /* 태블릿: 2열 */
    lg:grid-cols-3    /* 데스크톱: 3열 */
    gap-4
">
    {items.map(item => <Card key={item.id} {...item} />)}
</div>

// 반응형 여백
<div className="
    p-4              /* 모바일 */
    md:p-6           /* 태블릿 */
    lg:p-8           /* 데스크톱 */
">
```

### globals.css 커스텀

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 커스텀 컴포넌트 클래스 */
@layer components {
    .btn-primary {
        @apply px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors;
    }
    
    .btn-secondary {
        @apply px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors;
    }
    
    .card {
        @apply p-6 bg-white rounded-lg border border-gray-200 shadow-sm;
    }
    
    .input-field {
        @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent;
    }
}
```

```tsx
// 커스텀 클래스 사용
<button className="btn-primary">저장</button>
<div className="card">카드 내용</div>
<input className="input-field" placeholder="입력..." />
```

---

## 디버깅 팁

### 개발자 도구 활용

```tsx
// 컴포넌트에서 상태 디버깅
useEffect(() => {
    console.log('현재 상태:', { isLoggedIn, data, error });
}, [isLoggedIn, data, error]);
```

### 네트워크 요청 확인

1. 브라우저 개발자 도구 → Network 탭
2. `credentials: 'include'`가 포함된 요청 확인
3. Cookie 헤더에 `session_id`가 있는지 확인

### 흔한 실수들

```tsx
// ❌ 잘못된 예시: credentials 누락
fetch('/api/data');

// ✅ 올바른 예시
fetch('/api/data', { credentials: 'include' });


// ❌ 잘못된 예시: 환경변수 오타
process.env.NEXT_PUBLIC_API_URL  // 오타!

// ✅ 올바른 예시
process.env.NEXT_PUBLIC_API_BASE_URL


// ❌ 잘못된 예시: "use client" 누락
// 훅을 사용하는데 "use client" 없음
import { useState } from 'react';
export default function Page() {
    const [count, setCount] = useState(0);  // 에러!
}

// ✅ 올바른 예시
"use client";
import { useState } from 'react';
export default function Page() {
    const [count, setCount] = useState(0);  // OK
}
```

---

## 다음 단계

- [메인 온보딩 가이드](./README.md)로 돌아가기
- [백엔드 상세 가이드](./backend-deep-dive.md) 확인

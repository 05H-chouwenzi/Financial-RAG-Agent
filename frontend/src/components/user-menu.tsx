'use client';

import { useState, useEffect, type FormEvent } from 'react';
import { User } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

interface Account {
  nickname: string;
  password: string;
}

const USERS_KEY = 'finflow_users';
const SESSION_KEY = 'finflow_session';

function loadUsers(): Account[] {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveUsers(users: Account[]) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

export default function UserMenu() {
  const [open, setOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [current, setCurrent] = useState<Account | null>(null);
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // 恢复已登录会话
  useEffect(() => {
    try {
      const s = localStorage.getItem(SESSION_KEY);
      if (s) setCurrent(JSON.parse(s));
    } catch {
      // ignore
    }
  }, []);

  const switchMode = (login: boolean) => {
    setIsLogin(login);
    setError('');
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    const name = nickname.trim();
    if (!name || !password) {
      setError('请填写昵称和密码');
      return;
    }

    const users = loadUsers();

    if (isLogin) {
      // 登录：仅校验自注册账号
      const u = users.find((x) => x.nickname === name);
      if (!u) {
        setError('该昵称尚未注册，请先注册');
        return;
      }
      if (u.password !== password) {
        setError('密码错误');
        return;
      }
      setCurrent(u);
      localStorage.setItem(SESSION_KEY, JSON.stringify(u));
      setOpen(false);
      return;
    }

    // 注册
    if (users.some((x) => x.nickname === name)) {
      setError('该昵称已注册，请直接登录');
      return;
    }
    if (password.length < 6) {
      setError('密码至少 6 位');
      return;
    }
    const u: Account = { nickname: name, password };
    users.push(u);
    saveUsers(users);
    setCurrent(u);
    localStorage.setItem(SESSION_KEY, JSON.stringify(u));
    setNickname('');
    setPassword('');
    setOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setCurrent(null);
    setIsLogin(true);
    setError('');
  };

  // 已登录：显示昵称头像，点击退出
  if (current) {
    return (
      <button
        onClick={handleLogout}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
        title={`退出登录（${current.nickname}）`}
      >
        <Avatar className="h-7 w-7">
          <AvatarFallback className="text-xs bg-destructive/10 text-destructive">
            {current.nickname.slice(0, 1) || 'U'}
          </AvatarFallback>
        </Avatar>
      </button>
    );
  }

  return (
    <>
      <button
        onClick={() => {
          setIsLogin(true);
          setError('');
          setOpen(true);
        }}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
        title="登录 / 注册"
      >
        <User className="h-5 w-5" />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader className="items-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-8 w-8 text-destructive"
              >
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <DialogTitle className="text-xl">
              {isLogin ? '欢迎回来' : '创建账户'}
            </DialogTitle>
            <p className="text-sm text-muted-foreground">
              {isLogin ? '登录您的 FinFlow 账户' : '注册 FinFlow 账户'}
            </p>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">昵称</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="请输入昵称"
                className="flex h-11 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-destructive focus:outline-none focus:ring-1 focus:ring-destructive"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                className="flex h-11 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-destructive focus:outline-none focus:ring-1 focus:ring-destructive"
              />
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            <button
              type="submit"
              className="mt-2 h-11 w-full rounded-lg bg-destructive text-base font-semibold text-white shadow-lg shadow-destructive/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-destructive/30"
            >
              {isLogin ? '登录' : '注册'}
            </button>

            <p className="text-center text-sm text-muted-foreground">
              {isLogin ? '还没有账户？' : '已有账户？'}
              <button
                type="button"
                onClick={() => switchMode(!isLogin)}
                className="ml-1 font-medium text-destructive hover:underline"
              >
                {isLogin ? '立即注册' : '去登录'}
              </button>
            </p>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

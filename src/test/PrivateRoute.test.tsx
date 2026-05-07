import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PrivateRoute } from '../components/PrivateRoute';
import * as authHook from '@/components/useAuthState';
import { User } from 'firebase/auth';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';

vi.mock('@/components/useAuthState', () => ({
    useAuthState: vi.fn(),
}));

// Mock firebase signOut
vi.mock('firebase/auth', () => ({
    signOut: vi.fn(),
    getAuth: vi.fn(),
    onAuthStateChanged: vi.fn(() => vi.fn()),
    GoogleAuthProvider: vi.fn(),
}));

describe('PrivateRoute', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    const renderRoute = () => {
        return render(
            <MemoryRouter initialEntries={['/protected']}>
                <Routes>
                    <Route path="/login" element={<div>Login Page</div>} />
                    <Route
                        path="/protected"
                        element={
                            <PrivateRoute>
                                <div>Protected Content</div>
                            </PrivateRoute>
                        }
                    />
                </Routes>
            </MemoryRouter>
        );
    };

    it('redirects to /login when unauthenticated', async () => {
        // user is null, loading is false
        vi.mocked(authHook.useAuthState).mockReturnValue({ user: null, loading: false });

        renderRoute();

        await waitFor(() => {
            expect(screen.getByText('Login Page')).toBeInTheDocument();
        });
        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('renders children when authenticated with allowed email', async () => {
        // Ensuring the email fulfills the allow-list logic inside PrivateRoute
        const mockUser = { uid: '123', email: 'andreas@aaagents.de' } as unknown as User;
        // user is mockUser, loading is false
        vi.mocked(authHook.useAuthState).mockReturnValue({ user: mockUser, loading: false });
        renderRoute();

        await waitFor(() => {
            expect(screen.getByText('Protected Content')).toBeInTheDocument();
        });
    });
});

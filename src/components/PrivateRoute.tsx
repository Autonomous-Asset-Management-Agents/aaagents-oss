import { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { signOut } from "firebase/auth";
import { useAuthState } from "@/components/useAuthState";
import { auth } from "@/lib/firebase";

interface PrivateRouteProps {
    children: React.ReactNode;
}

// ── Operator Allowlist ──────────────────────────────────────────────────────
// Only these exact email addresses may access the console.
// Add or remove entries here + redeploy to change access.
const ALLOWED_DOMAIN = ""; // disabled — use explicit list below
const EXTRA_ALLOWED_EMAILS: string[] = [
    "andreas@aaagents.de",
    "georg@aaagents.de",
];

function isEmailAllowed(email: string | null | undefined): boolean {
    if (!email) return false;
    if (email.endsWith(`@${ALLOWED_DOMAIN}`)) return true;
    return EXTRA_ALLOWED_EMAILS.includes(email);
}
// ───────────────────────────────────────────────────────────────────────────

/**
 * Guards a route — redirects to /login if not authenticated.
 * Also enforces the operator email allowlist: unauthorised Google accounts
 * are signed out immediately and redirected with an error query param.
 */
export const PrivateRoute = ({ children }: PrivateRouteProps) => {
    const { user, loading } = useAuthState();

    // Sign out accounts that are authenticated but not on the allowlist
    useEffect(() => {
        if (!loading && user && !isEmailAllowed(user.email)) {
            signOut(auth);
        }
    }, [user, loading]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    // Still signed in but email not allowed → signed out above, show error
    if (!isEmailAllowed(user.email)) {
        return <Navigate to="/login?error=unauthorized" replace />;
    }

    return <>{children}</>;
};

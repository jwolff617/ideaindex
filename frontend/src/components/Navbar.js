import React, { useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { Button } from './ui/button';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Lightbulb, Map, Users, LogOut, Plus } from 'lucide-react';
import NotificationCenter from './NotificationCenter';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const Navbar = () => {
  const { user, logout, setShowAuthModal } = useContext(AuthContext);
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-gray-200" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-2 group" data-testid="logo-link">
            <div className="bg-gradient-to-br from-emerald-500 to-teal-600 p-2 rounded-xl group-hover:scale-105 transition-transform">
              <Lightbulb className="text-white" size={24} />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
              Idea Index
            </span>
          </Link>

          <div className="flex items-center space-x-6">
            <Link
              to="/"
              className={`text-sm font-medium transition-colors hover:text-emerald-600 ${isActive('/') ? 'text-emerald-600' : 'text-gray-600'}`}
              data-testid="nav-home"
            >
              Ideas
            </Link>
            <Link
              to="/map"
              className={`text-sm font-medium transition-colors hover:text-emerald-600 flex items-center space-x-1 ${isActive('/map') ? 'text-emerald-600' : 'text-gray-600'}`}
              data-testid="nav-map"
            >
              <Map size={16} />
              <span>Map</span>
            </Link>
            <Link
              to="/leaders"
              className={`text-sm font-medium transition-colors hover:text-emerald-600 flex items-center space-x-1 ${isActive('/leaders') ? 'text-emerald-600' : 'text-gray-600'}`}
              data-testid="nav-leaders"
            >
              <Users size={16} />
              <span>Leaders</span>
            </Link>

            {user && (
              <Link
                to="/collections"
                className={`text-sm font-medium transition-colors hover:text-emerald-600 flex items-center space-x-1 ${isActive('/collections') ? 'text-emerald-600' : 'text-gray-600'}`}
                data-testid="nav-collections"
              >
                <Bookmark size={16} />
                <span>Saved</span>
              </Link>
            )}

            {user ? (
              <>
                <Link to="/submit">
                  <Button className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700" data-testid="post-idea-button">
                    <Plus size={16} className="mr-1" />
                    Post Idea
                  </Button>
                </Link>
                <NotificationCenter />
                <DropdownMenu>
                  <DropdownMenuTrigger data-testid="user-menu-trigger">
                    <Avatar className="cursor-pointer ring-2 ring-emerald-500/20 hover:ring-emerald-500/40 transition-all">
                      <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white font-semibold">
                        {user.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                      <Link to={`/leaders/${user.username}`} className="cursor-pointer" data-testid="profile-link">
                        My Profile
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={logout} className="cursor-pointer text-red-600" data-testid="logout-button">
                      <LogOut size={16} className="mr-2" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <Button
                onClick={() => setShowAuthModal(true)}
                className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700"
                data-testid="signin-button"
              >
                Sign In
              </Button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

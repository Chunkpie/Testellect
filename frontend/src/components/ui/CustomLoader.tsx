import React from 'react';
import './CustomLoader.css';

interface CustomLoaderProps {
  message?: string;
}

export const CustomLoader: React.FC<CustomLoaderProps> = ({ message = "Generating..." }) => {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="relative w-full h-32 flex items-center justify-center mb-8">
        <div className="loader">
          <span><span></span><span></span><span></span><span></span></span>
          <div className="base">
            <span></span>
            <div className="face"></div>
          </div>
        </div>
        <div className="longfazers">
          <span></span><span></span><span></span><span></span>
        </div>
      </div>
      <h3 className="text-xl font-semibold mt-16 animate-pulse text-primary">{message}</h3>
    </div>
  );
};

import React from "react";
import { motion } from "framer-motion";

const AppTransition = ({
  children,
  type = "fade", // 'fade' | 'slide' | 'page'
  isVisible = true,
  delay = 0,
}) => {
  const variants = {
    fade: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
      transition: { duration: 0.2, delay },
    },
    slide: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -20 },
      transition: { duration: 0.3, delay },
    },
    page: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -20 },
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25,
        duration: 0.3,
        delay,
      },
    },
  };

  const currentVariant = variants[type];

  return (
    <motion.div
      initial={currentVariant.initial}
      animate={isVisible ? currentVariant.animate : currentVariant.initial}
      exit={currentVariant.exit}
      transition={currentVariant.transition}
      style={{
        visibility: isVisible ? "visible" : "hidden",
        opacity: isVisible ? 1 : 0,
      }}
    >
      {children}
    </motion.div>
  );
};

export default AppTransition;

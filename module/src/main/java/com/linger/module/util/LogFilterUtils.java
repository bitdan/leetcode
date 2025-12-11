package com.linger.module.util;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.Reader;
import java.io.Writer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * @description LogFilterUtils
 * @date 2025/4/7 09:25:02
 * @version 1.0
 */
public class LogFilterUtils {

    private static final Set<Class<?>> NON_LOGGABLE_TYPES = new HashSet<>();

    static {
        NON_LOGGABLE_TYPES.add(HttpServletRequest.class);
        NON_LOGGABLE_TYPES.add(HttpServletResponse.class);
        NON_LOGGABLE_TYPES.add(HttpSession.class);
        NON_LOGGABLE_TYPES.add(InputStream.class);
        NON_LOGGABLE_TYPES.add(OutputStream.class);
        NON_LOGGABLE_TYPES.add(Reader.class);
        NON_LOGGABLE_TYPES.add(Writer.class);
    }

    public static boolean isNonLoggable(Object obj) {
        return obj == null || isNonLoggableType(obj.getClass());
    }

    public static boolean isNonLoggableType(Class<?> clazz) {
        for (Class<?> nonLoggable : NON_LOGGABLE_TYPES) {
            if (nonLoggable.isAssignableFrom(clazz)) {
                return true;
            }
        }
        return false;
    }

    public static List<Object> filterLoggableArgs(Object[] args) {
        List<Object> result = new ArrayList<>();
        if (args != null) {
            for (Object arg : args) {
                if (!isNonLoggable(arg)) {
                    result.add(arg);
                }
            }
        }
        return result;
    }

    public static String stringifyLoggableArgs(Object[] args) {
        List<Object> filtered = filterLoggableArgs(args);
        StringBuilder sb = new StringBuilder();
        for (Object obj : filtered) {
            if (sb.length() > 0) {
                sb.append(", ");
            }
            sb.append(obj.toString());
        }
        return sb.toString();
    }
}

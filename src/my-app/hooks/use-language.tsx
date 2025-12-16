'use client';

import { createContext, useContext, useEffect, ReactNode, useMemo, useState, useCallback, startTransition } from 'react';
import { useSession } from '@/lib/auth/use-session';
import { LocaleManager } from '@/lib/locale-manager';

// Import English translation files from subdirectory
import enCommon from "@/locales/en/common.json";
import enConfirmDialog from "@/locales/en/confirmDialog.json";
import enNavbar from "@/locales/en/navbar.json";
import enUser from "@/locales/en/user.json";
import enUsers from "@/locales/en/users.json";
import enAuth from "@/locales/en/auth.json";
import enTheme from "@/locales/en/theme.json";
import enLanguage from "@/locales/en/language.json";
import enHome from "@/locales/en/home.json";
import enPages from "@/locales/en/pages.json";
import enTable from "@/locales/en/table.json";
import enRequests from "@/locales/en/requests.json";
import enMealRequest from "@/locales/en/mealRequest.json";
import enMealTypes from "@/locales/en/mealTypes.json";
import enSettingRoles from "@/locales/en/settingRoles.json";
import enAddUser from "@/locales/en/addUser.json";
import enAnalysis from "@/locales/en/analysis.json";
import enAudit from "@/locales/en/audit.json";
import enScheduler from "@/locales/en/scheduler.json";

// Import Arabic translation files from subdirectory
import arCommon from "@/locales/ar/common.json";
import arConfirmDialog from "@/locales/ar/confirmDialog.json";
import arNavbar from "@/locales/ar/navbar.json";
import arUser from "@/locales/ar/user.json";
import arUsers from "@/locales/ar/users.json";
import arAuth from "@/locales/ar/auth.json";
import arTheme from "@/locales/ar/theme.json";
import arLanguage from "@/locales/ar/language.json";
import arHome from "@/locales/ar/home.json";
import arPages from "@/locales/ar/pages.json";
import arTable from "@/locales/ar/table.json";
import arRequests from "@/locales/ar/requests.json";
import arMealRequest from "@/locales/ar/mealRequest.json";
import arMealTypes from "@/locales/ar/mealTypes.json";
import arSettingRoles from "@/locales/ar/settingRoles.json";
import arAddUser from "@/locales/ar/addUser.json";
import arAnalysis from "@/locales/ar/analysis.json";
import arAudit from "@/locales/ar/audit.json";
import arScheduler from "@/locales/ar/scheduler.json";

// Define the type for translation objects
type Translations = {
  [key: string]: string | Translations;
};

// Define the context properties
interface LanguageContextProps {
  language: 'en' | 'ar';
  t: Translations;
  dir: 'ltr' | 'rtl';
  setLanguage: (lang: 'en' | 'ar') => void;
}

// Merge all English translations into a single object
const en: Translations = {
  common: enCommon,
  confirmDialog: enConfirmDialog,
  navbar: enNavbar,
  user: enUser,
  users: enUsers,
  auth: enAuth,
  theme: enTheme,
  language: enLanguage,
  home: enHome,
  pages: enPages,
  table: enTable,
  requests: enRequests,
  mealRequest: enMealRequest,
  mealTypes: enMealTypes,
  settingRoles: enSettingRoles,
  addUser: enAddUser,
  analysis: enAnalysis,
  audit: enAudit,
  scheduler: enScheduler,
  // StatusPanel translations (commonly used across pages)
  statusPanel: {
    user: "User",
    users: "Users",
    role: "Role",
    roles: "Roles",
    job: "Job",
    jobs: "Jobs",
    active: "Active",
    inactive: "Inactive",
    all: "All",
    noRolesAvailable: "No roles available",
    clickToFilter: "Click to filter"
  },
  // MyRequests translations
  myRequests: {
    title: "My Requests",
    description: "View and track all your submitted meal requests",
    table: {
      id: "#",
      requestTime: "Request Time",
      closedTime: "Closed Time",
      notes: "Notes",
      mealType: "Type",
      totalRequests: "Requests",
      accepted: "Accepted",
      status: "Status",
      actions: "Actions",
      viewDetails: "View Details",
      copyRequest: "Copy Request",
      cannotCopyPending: "Cannot copy pending requests"
    },
    copySuccess: "Request copied successfully",
    copySuccessMessage: "New request #{id} created",
    copyError: "Copy failed",
    filters: {
      from: "From",
      to: "To",
      selectDate: "Select date",
      clearAll: "Clear all"
    },
    modal: {
      title: "Request Details",
      requestTime: "Request Time",
      mealType: "Meal Type",
      totalEmployees: "Total Employees",
      acceptedEmployees: "Accepted",
      closedOn: "Closed on",
      accepted: "accepted",
      rejected: "rejected",
      viewOnlyMessage: "This is a read-only view of your request",
      close: "Close",
      noRequestLines: "No request lines found",
      failedToLoad: "Failed to load details. Please try again."
    },
    lineTable: {
      rowNum: "#",
      code: "Code",
      employeeName: "Employee Name",
      title: "Title",
      department: "Department",
      shift: "Shift",
      status: "Status",
      notes: "Notes",
      actions: "Actions",
      deleteLine: "Delete Line"
    },
    deleteRequest: {
      title: "Delete Request?",
      message: "Are you sure you want to delete request #{{requestId}}? This will remove all {{totalLines}} request lines. This action cannot be undone.",
      confirm: "Delete",
      cancel: "Cancel"
    },
    deleteLine: {
      title: "Delete Employee Line?",
      message: "Are you sure you want to remove {{employeeName}} from this request? This action cannot be undone.",
      confirm: "Delete",
      cancel: "Cancel"
    },
    deleteSuccess: "Request deleted successfully",
    deleteSuccessMessage: "Request #{{requestId}} and its {{totalLines}} lines have been deleted",
    deleteError: "Delete failed",
    deleteLineSuccess: "Employee removed successfully",
    deleteLineSuccessMessage: "{{employeeName}} has been removed from the request",
    deleteLineError: "Failed to remove employee",
    empty: {
      title: "No requests found",
      description: "You haven't submitted any meal requests yet"
    }
  },
  // DatePicker translations
  datePicker: {
    placeholder: "Pick a date range",
    from: "From",
    to: "To",
    clear: "Clear",
    apply: "Apply",
    presets: {
      title: "Presets",
      today: "Today",
      yesterday: "Yesterday",
      last7Days: "Last 7 days",
      last30Days: "Last 30 days",
      thisWeek: "This week",
      thisMonth: "This month"
    }
  }
};

// Merge all Arabic translations into a single object
const ar: Translations = {
  common: arCommon,
  confirmDialog: arConfirmDialog,
  navbar: arNavbar,
  user: arUser,
  users: arUsers,
  auth: arAuth,
  theme: arTheme,
  language: arLanguage,
  home: arHome,
  pages: arPages,
  table: arTable,
  requests: arRequests,
  mealRequest: arMealRequest,
  mealTypes: arMealTypes,
  settingRoles: arSettingRoles,
  addUser: arAddUser,
  analysis: arAnalysis,
  audit: arAudit,
  scheduler: arScheduler,
  // StatusPanel translations (commonly used across pages)
  statusPanel: {
    user: "مستخدم",
    users: "مستخدمين",
    role: "صلاحية",
    roles: "صلاحيات",
    job: "مهمة",
    jobs: "مهام",
    active: "نشط",
    inactive: "غير نشط",
    all: "الكل",
    noRolesAvailable: "لا توجد صلاحيات متاحة",
    clickToFilter: "انقر للتصفية"
  },
  // MyRequests translations
  myRequests: {
    title: "طلباتي",
    description: "عرض وتتبع جميع طلبات الوجبات المقدمة",
    table: {
      id: "#",
      requestTime: "وقت الطلب",
      closedTime: "وقت الإغلاق",
      notes: "ملاحظات",
      mealType: "النوع",
      totalRequests: "الطلبات",
      accepted: "مقبول",
      status: "الحالة",
      actions: "الإجراءات",
      viewDetails: "عرض التفاصيل",
      copyRequest: "نسخ الطلب",
      cannotCopyPending: "لا يمكن نسخ الطلبات المعلقة"
    },
    copySuccess: "تم نسخ الطلب بنجاح",
    copySuccessMessage: "تم إنشاء طلب جديد #{id}",
    copyError: "فشل النسخ",
    filters: {
      from: "من",
      to: "إلى",
      selectDate: "اختر التاريخ",
      clearAll: "مسح الكل"
    },
    modal: {
      title: "تفاصيل الطلب",
      requestTime: "وقت الطلب",
      mealType: "نوع الوجبة",
      totalEmployees: "إجمالي الموظفين",
      acceptedEmployees: "مقبول",
      closedOn: "أُغلق في",
      accepted: "مقبول",
      rejected: "مرفوض",
      viewOnlyMessage: "هذا عرض للقراءة فقط لطلبك",
      close: "إغلاق",
      noRequestLines: "لا توجد طلبات",
      failedToLoad: "فشل تحميل التفاصيل. يرجى المحاولة مرة أخرى."
    },
    lineTable: {
      rowNum: "#",
      code: "الكود",
      employeeName: "اسم الموظف",
      title: "المسمى الوظيفي",
      department: "القسم",
      shift: "الوردية",
      status: "الحالة",
      notes: "ملاحظات",
      actions: "الإجراءات",
      deleteLine: "حذف السطر"
    },
    deleteRequest: {
      title: "حذف الطلب؟",
      message: "هل أنت متأكد من حذف الطلب #{{requestId}}؟ سيؤدي هذا إلى إزالة جميع سطور الطلب ({{totalLines}}). لا يمكن التراجع عن هذا الإجراء.",
      confirm: "حذف",
      cancel: "إلغاء"
    },
    deleteLine: {
      title: "حذف سطر الموظف؟",
      message: "هل أنت متأكد من إزالة {{employeeName}} من هذا الطلب؟ لا يمكن التراجع عن هذا الإجراء.",
      confirm: "حذف",
      cancel: "إلغاء"
    },
    deleteSuccess: "تم حذف الطلب بنجاح",
    deleteSuccessMessage: "تم حذف الطلب #{{requestId}} و{{totalLines}} سطور",
    deleteError: "فشل الحذف",
    deleteLineSuccess: "تمت إزالة الموظف بنجاح",
    deleteLineSuccessMessage: "تمت إزالة {{employeeName}} من الطلب",
    deleteLineError: "فشلت إزالة الموظف",
    empty: {
      title: "لا توجد طلبات",
      description: "لم تقم بتقديم أي طلبات وجبات بعد"
    }
  },
  // DatePicker translations
  datePicker: {
    placeholder: "اختر نطاق التاريخ",
    from: "من",
    to: "إلى",
    clear: "مسح",
    apply: "تطبيق",
    presets: {
      title: "الإعدادات المسبقة",
      today: "اليوم",
      yesterday: "أمس",
      last7Days: "آخر 7 أيام",
      last30Days: "آخر 30 يوم",
      thisWeek: "هذا الأسبوع",
      thisMonth: "هذا الشهر"
    }
  }
};

// Store the translations for each language
const translations: { [lang: string]: Translations } = {
  en,
  ar,
};

// Create the context
const LanguageContext = createContext<LanguageContextProps | undefined>(undefined);

// Props for the LanguageProvider
interface LanguageProviderProps {
  children: ReactNode;
  initialLanguage?: 'en' | 'ar';
}

/**
 * LanguageProvider component that provides the current language and translations.
 *
 * Single source of truth: cookies (via LocaleManager)
 *
 * Priority order:
 * 1. Cookie (user's explicit choice / server-set after login)
 * 2. Session locale as fallback
 * 3. Initial language from server as final fallback
 *
 * On first load, LocaleManager automatically migrates any existing localStorage
 * locale to cookies and syncs with the backend.
 *
 * The setLanguage function allows components like LanguageSwitcher to
 * trigger immediate re-renders and update the cookie.
 */
export const LanguageProvider = ({
  children,
  initialLanguage = 'en'
}: LanguageProviderProps) => {
  const { user } = useSession();

  // State for current language - allows immediate updates
  const [language, setLanguageState] = useState<'en' | 'ar'>(() => {
    // On initial render (server), use initialLanguage
    if (typeof window === 'undefined') {
      return initialLanguage;
    }
    // On client, check cookie first for immediate value (also triggers migration)
    return LocaleManager.getLocale();
  });

  // Sync language from cookie/session on mount and when user changes
  // Using startTransition to avoid blocking renders
  useEffect(() => {
    const cookieLocale = LocaleManager.getLocale();
    const sessionLocale = user?.locale;

    // Priority: cookie > session > initial
    if (cookieLocale === 'ar' || cookieLocale === 'en') {
      startTransition(() => setLanguageState(cookieLocale));
    } else if (sessionLocale === 'ar' || sessionLocale === 'en') {
      startTransition(() => setLanguageState(sessionLocale));
    }
  }, [user, initialLanguage]);

  // Function to update language immediately (updates cookie + state)
  const setLanguage = useCallback((newLang: 'en' | 'ar') => {
    LocaleManager.setLocale(newLang); // Updates cookie
    setLanguageState(newLang);        // Updates React state for immediate re-render
  }, []);

  // Sync document direction and font when language changes
  useEffect(() => {
    const dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.setAttribute('dir', dir);
    document.documentElement.setAttribute('lang', language);

    // Update body font class
    if (language === 'ar') {
      document.body.classList.add('font-cairo');
    } else {
      document.body.classList.remove('font-cairo');
    }

  }, [language]);

  const contextValue: LanguageContextProps = useMemo(() => ({
    language,
    t: translations[language],
    dir: language === 'ar' ? 'rtl' : 'ltr',
    setLanguage,
  }), [language, setLanguage]);

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
};

/**
 * Custom hook to consume the LanguageContext.
 * @throws Will throw an error if used outside of a LanguageProvider.
 */
export const useLanguage = (): LanguageContextProps => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

/**
 * Helper function to get nested translation value by dot notation key.
 * Usage: translate(t, 'navbar.title')
 */
export const translate = (translations: Translations, key: string): string => {
  const keys = key.split('.');
  let result: string | Translations = translations;

  for (const k of keys) {
    if (typeof result === 'object' && result !== null && k in result) {
      result = result[k];
    } else {
      return key; // Return key if translation not found
    }
  }

  return typeof result === 'string' ? result : key;
};
